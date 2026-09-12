"""Fixed original values through real roots, actual consumers and hostile envelopes."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys

import pytest

from pietto.ast_nodes import LiteralExpr, UnaryExpr
from pietto.semantic.model import TypeKind, ValueTypeKind
from pietto._project import project_sql_plan as planner
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_literals as literal
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_verification as verification
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
    _roots,
    _graft,
)
from test_phase65_slice4_row_scalar_let_where_stage_value_planning import _source
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _source as _join_source,
)
from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
    _repeated_sets,
)
from test_phase65_slice6_grouped_global_satisfying_block_boundaries import _ordinary
from test_phase65_slice7_windows_named_window_qualify_staging import _family_source

P = literal.ProjectSQLLiteralPolicy
R = literal.ProjectSQLLiteralRole
Why = literal.ProjectSQLLiteralReason

BODY = """    let:
        a = 1
        b = 1.0
        c = true
        d = "text"
    where true and 1 == 1 and 1.0 > 0.0 and "x" == "x"
    select:
        n = -3
        z = -0.0
        f = 1.25
        t = "é\\n😀"
        flag = false
        huge = 123456789012345678901234567890123456789
        first = a
        again = a
"""


def _product(path, source, policy=P.BIND_SAFE_LITERALS):
    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = planner.build_project_sql_plan(*roots, literal_policy=policy)
    assert isinstance(plan, planner.ProjectSQLPlan), getattr(plan, "blockers", ())
    checked = verification.verify_project_sql_plan(plan, *roots, literal_policy=policy)
    assert checked.verified, checked.issues
    return roots, plan, checked, inspect_project_sql_plan(checked)


@pytest.fixture(scope="module")
def products(tmp_path_factory):
    joined = _join_source('true and 1 == 1 and 1.0 > 0.0 and "x" == "x"').replace(
        "    select:\n        id = lhs.id\n", BODY
    )
    return tuple(
        _product(tmp_path_factory.mktemp("literals"), source)
        for source in (_source(BODY), joined)
    )


@pytest.mark.parametrize("index", (0, 1))
def test_all_tags_in_real_eligible_contexts_and_consumers(products, index):
    roots, plan, _, view = products[index]
    tags = set(literal.ProjectSQLLiteralTag)
    roles = (
        (R.LET, R.WHERE, R.SELECT) if index == 0 else (R.ON, R.LET, R.WHERE, R.SELECT)
    )
    for role in roles:
        assert {
            slot.tag for slot in view.literal_slots if slot.site.position.role is role
        } == tags
    assert view.literal_policy is P.BIND_SAFE_LITERALS
    assert (
        len(view.literal_slots)
        == len(view.bind_uses)
        == len(view.fixed_envelope.values)
    )
    for slot, use, value in zip(
        view.literal_slots, view.bind_uses, view.fixed_envelope.values, strict=True
    ):
        assert (
            value.slot is use.slot is slot
            and use.expression is slot.site.position.expression
        )
        expression = view.expression(use.expression)
        assert type(expression) is row.ProjectSQLBoundLiteral
        assert expression.expression is slot.site.position.literal
        assert expression.value_type is slot.value_type is slot.site.position.value_type
        assert expression.use is use
        assert view.literal_value(expression.ref) is view.fixed_value(slot.ref) is value
        assert view.uses_for_slot(slot.ref) == (use,)
        assert view.literal_site(slot.site.ref) is slot.site
        (demand,) = view.literal_requirements(slot.ref)
        assert demand.use is use and demand.value is value
        assert demand.contexts[-1].expression is expression.expression
        assert demand.contexts[-1].value_type is expression.value_type
        assert demand.requirements == tuple(literal.ProjectSQLLiteralRequirement)
        assert literal.same_value(value.tag, value.value, expression.expression.value)
    assert plan.scope.completed is roots[0]
    assert all(
        site.reason is Why.SPECIALIZED
        for site in view.literal_sites
        if site.position.role is R.CONNECTOR
    )


def test_default_and_explicit_preserve_parity(products):
    roots, _, _, _ = products[0]
    default = planner.build_project_sql_plan(*roots)
    explicit = planner.build_project_sql_plan(
        *roots, literal_policy=P.PRESERVE_LITERALS
    )
    assert isinstance(default, planner.ProjectSQLPlan) and isinstance(
        explicit, planner.ProjectSQLPlan
    )
    for plan in (default, explicit):
        checked = verification.verify_project_sql_plan(plan, *roots)
        assert checked.verified, checked.issues
        view = inspect_project_sql_plan(checked)
        assert plan.literal_slots == plan.bind_uses == plan.fixed_envelope.values == ()
        assert all(site.reason is Why.POLICY for site in plan.literal_sites)
        assert all(
            site.disposition
            is literal.ProjectSQLLiteralDisposition.PRESERVED_WITH_REASON
            for site in plan.literal_sites
        )
        for expression in plan.expressions:
            if type(expression) is row.ProjectSQLLiteral:
                assert view.literal_value(expression.ref) is expression
    assert [
        (s.position.literal, s.position.role, s.position.value_type)
        for s in default.literal_sites
    ] == [
        (s.position.literal, s.position.role, s.position.value_type)
        for s in explicit.literal_sites
    ]
    assert [type(e) for e in default.expressions] == [
        type(e) for e in explicit.expressions
    ]
    assert len(default.demands) == len(explicit.demands)


@pytest.mark.parametrize("policy", tuple(P))
def test_empty_fixed_envelope_requires_actual_zero_bound_sites(tmp_path, policy):
    _, plan, _, view = _product(tmp_path, _source("    select:\n        id\n"), policy)
    assert len(plan.literal_sites) == 1
    assert plan.literal_sites[0].position.role is R.CONNECTOR
    assert view.fixed_envelope.values == view.fixed_envelope.slots == ()
    assert verification.verify_fixed_literal_envelope(
        plan, plan.fixed_envelope, literal_policy=policy
    )


def test_equal_values_remain_separate_and_let_references_do_not_reextract(products):
    _, plan, _, view = products[0]
    ones = [
        slot
        for slot in plan.literal_slots
        if slot.tag is literal.ProjectSQLLiteralTag.INT
        and slot.site.position.literal.value == 1
    ]
    assert len(ones) == 3
    assert len({slot.ref for slot in ones}) == 3
    let = plan.let_values[0]
    use = next(use for use in plan.bind_uses if use.expression is let.expression)
    assert view.uses_for_slot(use.slot.ref) == (use,)
    assert (
        sum(
            isinstance(e, row.ProjectSQLReference)
            and e.reference.let_candidates == (let.site.occurrence,)
            for e in plan.expressions
        )
        == 2
    )


def test_unary_sign_unicode_and_large_int_are_original_values(products):
    _, plan, _, view = products[0]
    negatives = [e for e in plan.expressions if isinstance(e, row.ProjectSQLUnary)]
    assert len(negatives) == 2
    for expression in negatives:
        assert (
            type(expression.expression) is UnaryExpr
            and expression.expression.operator == "-"
        )
        child = view.expression(expression.operand)
        assert type(child) is row.ProjectSQLBoundLiteral
        assert child.expression is expression.expression.operand
    zero = view.literal_value(negatives[1].operand)
    assert (
        isinstance(zero, literal.ProjectSQLFixedLiteralValue)
        and type(zero.value) is float
    )
    assert zero.value.hex() == "0x0.0p+0"
    text = next(value for value in plan.fixed_envelope.values if value.value == "é\n😀")
    position = text.slot.site.position
    assert text.slot.site.span is position.literal.span
    # Parser coordinates count authored characters, not decoded string length.
    assert text.slot.site.span.end_column - text.slot.site.span.column == len(
        '"é\\n😀"'
    )
    assert view.fixed_value(text.slot.ref).value == "é\n😀"
    huge = next(
        value
        for value in plan.fixed_envelope.values
        if type(value.value) is int and value.value > 2**63
    )
    assert huge.value == 123456789012345678901234567890123456789


@pytest.mark.parametrize(
    "body",
    (
        "    select:\n        x = sum(value * 2 + 1)\n",
        "    group by:\n        id\n    select:\n        id\n        x = count(value + 1)\n    satisfying:\n        x > 2\n",
        "    select:\n        x = count(len(label) + 1)\n",
    ),
)
def test_admitted_aggregate_call_and_satisfying_contexts_are_preserved(tmp_path, body):
    source = _ordinary(body).replace(
        "    value: Int nullable\n",
        "    value: Int nullable\n    label: Text nullable\n",
    )
    _, plan, _, _ = _product(tmp_path, source)
    assert plan.aggregates and not plan.literal_slots
    assert any(
        site.position.role is R.AGGREGATE_ARGUMENT for site in plan.literal_sites
    )
    assert all(site.reason is Why.SPECIALIZED for site in plan.literal_sites)
    if plan.filters:
        assert any(site.position.role is R.SATISFYING for site in plan.literal_sites)


@pytest.mark.parametrize(
    "call",
    (
        "lag(value, 2, 0)",
        "lag(value, 1, null)",
        "lag(5, 1, 0)",
        "lead(value)",
        "ntile(3)",
    ),
)
def test_authored_window_literals_defaults_and_missing_types(tmp_path, call):
    _, plan, _, _ = _product(
        tmp_path, _family_source(call, None, False, "query", "postgres")
    )
    arguments = [
        site for site in plan.literal_sites if site.position.role is R.WINDOW_ARGUMENT
    ]
    assert len(arguments) == sum(
        type(a.expression) is LiteralExpr for a in plan.window_arguments
    )
    assert plan.literal_slots == ()
    for site in arguments:
        assert site.reason is Why.SPECIALIZED
        assert site.position.evidence is site.position.context
        assert type(site.position.context) is windows.ProjectSQLWindowArgument
        assert site.position.value_type is site.position.context.value_type
    if call == "lead(value)":
        assert arguments == []  # Effective offset/default scalars are not authored AST.
    if call.startswith("lag"):
        assert any(site.position.value_type is None for site in arguments)


@pytest.mark.parametrize("named", (False, True))
def test_frame_ast_literals_retain_each_actual_window_context(tmp_path, named):
    source = _family_source(
        "first_value(value)",
        "rows between 2 preceding and current row",
        named,
        "query",
        "postgres",
    )
    if named:
        source = source.replace(
            "        w = first_value(value) window composed\n",
            "        w = first_value(value) window composed\n        another = last_value(value) window composed\n",
        )
    _, plan, _, _ = _product(tmp_path, source)
    frames = [site for site in plan.literal_sites if site.position.role is R.FRAME]
    assert len(frames) == (2 if named else 1)
    assert all(site.reason is Why.SPECIALIZED for site in frames)
    if named:
        assert frames[0].position.literal is frames[1].position.literal
        assert frames[0].position.context is not frames[1].position.context


def test_order_limit_zero_and_qualify_do_not_erase_defining_literals(tmp_path):
    source = _source("""    let:
        v = id + 1
    select:
        constant = 2
    qualify:
        row_number() window:
            order by:
                id
        <= 3
    order by:
        v + 4
    limit 0
""")
    _, plan, _, _ = _product(tmp_path, source)
    assert [value.value for value in plan.fixed_envelope.values] == [1, 2]
    assert plan.result_limits[0].value == 0 and plan.windows and plan.order_uses
    assert {
        site.position.role
        for site in plan.literal_sites
        if site.reason is Why.SPECIALIZED
    } == {R.CONNECTOR, R.QUALIFY, R.ORDER, R.LIMIT}


def test_bound_earlier_let_flows_through_aggregate_port(tmp_path):
    source = _ordinary("""    let:
        key = id
        amount = value + 1
    where false
    group by:
        key
    select:
        total = sum(amount)
    satisfying:
        total > 0 and sum(amount) > 1
""")
    _, plan, _, view = _product(tmp_path, source)
    assert [value.value for value in plan.fixed_envelope.values] == [1, False]
    (argument,) = view.arguments_for_aggregate(plan.aggregates[0].ref)
    assert isinstance(argument, row.ProjectSQLReference)
    assert all(
        site.position.role is not R.AGGREGATE_ARGUMENT for site in plan.literal_sites
    )


def test_depth12_named_definitions_keep_one_defining_slot(tmp_path):
    source = _repeated_sets(12).replace("        id\n", "        id = 17\n", 1)
    _, plan, _, view = _product(tmp_path, source)
    assert len(plan.bindings.definitions) == 15 and len(plan.input_uses) == 26
    assert len(plan.set_bodies) == 12 and len(plan.set_operands) == 24
    assert len(plan.literal_slots) == len(plan.bind_uses) == 1
    assert view.fixed_envelope.values[0].value == 17
    assert view.literal_slots[0].site.position.owner.definition.name == "p0"


@pytest.mark.parametrize("family,kind", (("postgres", "query"), ("mysql", "table")))
@pytest.mark.parametrize(
    "join", ("inner", "left", "right", "full", "semi", "anti", "cross")
)
def test_bound_transport_keeps_all_seven_join_shapes(tmp_path, family, kind, join):
    source = _join_source(None if join == "cross" else "lhs.id > 1 and true", kind=join)
    source = source.replace("postgres.table", family + ".table").replace(
        "query result:", kind + " result:"
    )
    source += '        constant = "value"\n'
    _, plan, _, view = _product(tmp_path, source)
    assert len(plan.joins) == 1 and len(plan.join_inputs) == 2
    assert len(plan.literal_slots) == (1 if join == "cross" else 3)
    assert [p.identity.name for p in view.exports] == ["id", "constant"]


def test_imported_reexported_set_uses_keep_defining_source_and_slots(tmp_path: Path):
    producer = _source("    select:\n        v = 17\n").replace(
        "query result:", "table first:"
    )
    (tmp_path / "a.pietto").write_text(producer + "export:\n    table first\n")
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    source = 'import "b.pietto":\n    table Public as Alias\nquery result:\n    union all:\n        from Alias\n        from Alias\n'
    _, plan, _, view = _product(tmp_path, source)
    assert len(plan.literal_slots) == 1 and len(plan.set_operands) == 2
    slot = plan.literal_slots[0]
    assert slot.site.position.owner.definition.name == "first"
    assert slot.site.span.path == "a.pietto"
    assert plan.set_operands[0].producer is plan.set_operands[1].producer
    assert all(
        operand.use.binding.imported_binding is not None
        and len(operand.use.origin_path.hops) == 2
        for operand in plan.set_operands
    )
    assert view.fixed_value(slot.ref).value == 17


@pytest.mark.parametrize(
    "operation",
    (
        "union all",
        "union distinct",
        "intersect all",
        "intersect distinct",
        "except all",
        "except distinct",
    ),
)
def test_set_membership_keeps_equal_definitions_and_limit_zero(tmp_path, operation):
    prefix = _source("    select:\n        id = 1\n    limit 0\n").replace(
        "query result:", "table left:"
    )
    source = (
        prefix
        + f"table right:\n    from rows\n    select:\n        other = 1\nquery result:\n    {operation}:\n        from left\n        from right\n"
    )
    _, plan, _, view = _product(tmp_path, source)
    assert len(plan.literal_slots) == 2 and [
        v.value for v in view.fixed_envelope.values
    ] == [1, 1]
    assert (
        plan.literal_slots[0].site.position.owner
        is not plan.literal_slots[1].site.position.owner
    )
    assert plan.result_limits[0].value == 0
    assert len(plan.set_columns[0].inputs) == 2
    assert len(plan.set_columns[0].value_inputs) == (
        1 if operation.startswith("except") else 2
    )
    assert all(view.literal_requirements(slot.ref) for slot in plan.literal_slots)


@pytest.mark.parametrize(
    "operation",
    (
        "union all",
        "union distinct",
        "intersect all",
        "intersect distinct",
        "except all",
        "except distinct",
    ),
)
def test_finite_float_binding_does_not_approve_row_equivalence(tmp_path, operation):
    source = _source("    select:\n        id = 1.5\n").replace(
        "query result:", "table operand:"
    )
    source += (
        f"query result:\n    {operation}:\n        from operand\n        from operand\n"
    )
    roots = _roots(tmp_path, source)
    plan = planner.build_project_sql_plan(*roots, literal_policy=P.BIND_SAFE_LITERALS)
    if operation == "union all":
        assert isinstance(plan, planner.ProjectSQLPlan)
        assert verification.verify_project_sql_plan(
            plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
        ).verified
        assert (
            len(plan.literal_slots) == 1 and not plan.set_bodies[0].requires_equivalence
        )
    else:
        assert not roots[0].ok and isinstance(plan, planner.ProjectSQLPlanUnavailable)
        assert roots[0].diagnostics


@pytest.mark.parametrize("bridge", (False, True))
def test_direct_set_aggregation_boundary_and_explicit_bridge_stay_unchanged(
    tmp_path, bridge
):
    source = (
        _repeated_sets(1)
        .split("query result:")[0]
        .replace("        id\n", "        id = 2\n", 1)
    )
    source += "table bridge:\n    from p1\n    select:\n        id\n" if bridge else ""
    source += f"query result:\n    from {'bridge' if bridge else 'p1'}\n    select:\n        n = count()\n"
    roots = _roots(tmp_path, source)
    plan = planner.build_project_sql_plan(*roots, literal_policy=P.BIND_SAFE_LITERALS)
    if bridge:
        assert isinstance(plan, planner.ProjectSQLPlan)
        assert verification.verify_project_sql_plan(
            plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
        ).verified
        assert len(plan.literal_slots) == 1 and plan.aggregates
    else:
        assert not roots[0].ok and "PIE-S2333" in [d.code for d in roots[0].diagnostics]
        assert isinstance(plan, planner.ProjectSQLPlanUnavailable)


def test_computed_let_window_prerequisite_remains_negative(tmp_path):
    source = _ordinary(
        "    let:\n        v = value + 1\n    select:\n        id\n        v\n"
    ).replace("query result:", "table earlier:")
    source += "query result:\n    from earlier\n    select:\n        w = lag(v, 1, 0) window:\n            order by:\n                id\n    order by:\n        w\n"
    roots = _roots(tmp_path, source)
    assert not roots[0].ok and "PIE-S2104" in [d.code for d in roots[0].diagnostics]
    for policy in P:
        assert isinstance(
            planner.build_project_sql_plan(*roots, literal_policy=policy),
            planner.ProjectSQLPlanUnavailable,
        )


def test_bound_mode_keeps_single_match_warning_through_except_membership(tmp_path):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots as join_roots,
        _requests,
    )

    source = _join_source("true").replace("query result:", "table operand:")
    source = source.replace("        id = lhs.id\n", "        id = 7\n")
    source += "query result:\n    except all:\n        from lhs\n        from operand\n"
    # Match the original source width without changing its nullable/key evidence.
    source = source.replace(
        "        id = 7\n",
        "        id = 7\n        key = lhs.key\n        allow_any = lhs.allow_any\n",
    )
    roots = join_roots(tmp_path, source, _requests)
    assert roots[0].ok, roots[0].diagnostics
    plan = planner.build_project_sql_plan(*roots, literal_policy=P.BIND_SAFE_LITERALS)
    assert isinstance(plan, planner.ProjectSQLPlan)
    checked = verification.verify_project_sql_plan(
        plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert checked.verified, checked.issues
    assert plan.single_matches and any(d.code == "PIE-S2337" for d in plan.diagnostics)
    assert len(plan.literal_slots) == 2 and plan.set_bodies
    assert len(plan.set_columns[0].value_inputs) == 1


def _tuple_replaced(values, old, new):
    return tuple(new if value is old else value for value in values)


def _rejected(roots, plan, candidate):
    assert not verification.verify_fixed_literal_envelope(
        candidate, candidate.fixed_envelope, literal_policy=P.BIND_SAFE_LITERALS
    )
    checked = verification.verify_project_sql_plan(
        candidate, *roots, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert not checked.verified
    stale = _graft(
        verification.verify_project_sql_plan(
            plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
        ),
        plan=candidate,
    )
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(stale)


@pytest.mark.parametrize("collection", ("literal_sites", "literal_slots", "bind_uses"))
@pytest.mark.parametrize(
    "corruption", ("empty", "missing", "extra", "duplicate", "reordered", "mutable")
)
def test_complete_ordered_schema_and_use_inventories(products, collection, corruption):
    roots, plan, _, _ = products[0]
    values = getattr(plan, collection)
    changed = {
        "empty": (),
        "missing": values[:-1],
        "extra": (*values, values[0]),
        "duplicate": (values[0], *values[:-1]),
        "reordered": tuple(reversed(values)),
        "mutable": list(values),
    }[corruption]
    _rejected(roots, plan, _graft(plan, **{collection: changed}))


@pytest.mark.parametrize(
    "field",
    (
        "definition",
        "owner",
        "context",
        "context_ref",
        "literal",
        "value_type",
        "evidence",
        "expression",
        "role",
        "ancestry",
    ),
)
def test_context_role_type_and_source_identity_are_not_payload_equality(
    products, field
):
    roots, plan, _, _ = products[0]
    site = plan.literal_slots[0].site
    other = plan.literal_slots[1].site
    replacement = getattr(other.position, field)
    if replacement is getattr(site.position, field):
        replacement = None
    if field == "role":
        replacement = R.ORDER
    if field == "ancestry":
        replacement = ((site.position.literal, True),)
    bad = _graft(site, position=_graft(site.position, **{field: replacement}))
    _rejected(
        roots,
        plan,
        _graft(plan, literal_sites=_tuple_replaced(plan.literal_sites, site, bad)),
    )


@pytest.mark.parametrize(
    "change", ("span", "reason", "disposition", "ordinal", "structural")
)
def test_literal_correspondence_and_positive_eligibility(products, change):
    roots, plan, _, _ = products[0]
    site = (
        plan.literal_sites[0] if change == "structural" else plan.literal_slots[0].site
    )
    changes = {
        "span": {"span": None},
        "reason": {"reason": Why.TYPE_UNAVAILABLE},
        "disposition": {
            "disposition": literal.ProjectSQLLiteralDisposition.PRESERVED_WITH_REASON
        },
        "ordinal": {"ref": _graft(site.ref, position=True)},
        "structural": {
            "reason": None,
            "disposition": literal.ProjectSQLLiteralDisposition.BOUND,
        },
    }[change]
    bad = _graft(site, **changes)
    _rejected(
        roots,
        plan,
        _graft(plan, literal_sites=_tuple_replaced(plan.literal_sites, site, bad)),
    )


@pytest.mark.parametrize(
    "corruption",
    (
        "empty",
        "extra",
        "duplicate",
        "reordered",
        "mutable",
        "wrong_tag",
        "changed_value",
        "foreign_slot",
        "policy",
        "scope",
    ),
)
def test_fixed_envelope_independently_rejects_malformed_or_rebound_values(
    products, corruption
):
    roots, plan, _, _ = products[0]
    envelope = plan.fixed_envelope
    values = envelope.values
    wrong = _graft(values[0], value=22)
    changes = {
        "empty": {"values": ()},
        "extra": {"values": (*values, values[0])},
        "duplicate": {"values": (values[0], *values[:-1])},
        "reordered": {"values": tuple(reversed(values))},
        "mutable": {"values": list(values)},
        "wrong_tag": {
            "values": (
                _graft(values[0], tag=literal.ProjectSQLLiteralTag.BOOL),
                *values[1:],
            )
        },
        "changed_value": {"values": (wrong, *values[1:])},
        "foreign_slot": {"slots": products[1][1].literal_slots},
        "policy": {"policy": P.PRESERVE_LITERALS},
        "scope": {"scope": products[1][1].scope},
    }[corruption]
    _rejected(roots, plan, _graft(plan, fixed_envelope=_graft(envelope, **changes)))


@pytest.mark.parametrize(
    "tag,value",
    (
        ("Int", True),
        ("Int", 1.0),
        ("Float", 1),
        ("Bool", 1),
        ("Text", b"text"),
        ("Float", float("inf")),
        ("Float", float("nan")),
    ),
)
def test_exact_numeric_tags_and_finite_float(products, tag, value):
    _, plan, _, _ = products[0]
    original = next(v for v in plan.fixed_envelope.values if v.tag.value == tag)
    bad = _graft(original, value=value)
    envelope = _graft(
        plan.fixed_envelope,
        values=_tuple_replaced(plan.fixed_envelope.values, original, bad),
    )
    assert not verification.verify_fixed_literal_envelope(
        plan, envelope, literal_policy=P.BIND_SAFE_LITERALS
    )


def test_signed_zero_payload_corruption_does_not_fold_unary_minus(products):
    roots, plan, _, _ = products[0]
    original = next(
        v
        for v in plan.fixed_envelope.values
        if v.tag is literal.ProjectSQLLiteralTag.FLOAT
        and v.value == 0.0
        and v.slot.site.position.role is R.SELECT
    )
    assert type(original.value) is float and original.value.hex() == "0x0.0p+0"
    bad = _graft(original, value=-0.0)
    envelope = _graft(
        plan.fixed_envelope,
        values=_tuple_replaced(plan.fixed_envelope.values, original, bad),
    )
    _rejected(roots, plan, _graft(plan, fixed_envelope=envelope))


def test_policy_and_envelope_identity_invalidate_old_verification(products):
    roots, plan, checked, _ = products[0]
    assert not verification.verify_project_sql_plan(plan, *roots).verified
    copied = replace(plan.fixed_envelope)
    assert verification.verify_fixed_literal_envelope(
        plan, copied, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert not verification.verify_project_sql_plan(
        plan, *roots, literal_policy=P.BIND_SAFE_LITERALS, envelope=copied
    ).verified
    for stale in (
        _graft(checked, literal_policy=P.PRESERVE_LITERALS),
        _graft(checked, envelope=copied),
        _graft(checked, plan=_graft(plan, fixed_envelope=copied)),
    ):
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(stale)
    changed = _graft(plan, fixed_envelope=copied)
    # Identical content requires fresh verification and matching origin witnesses.
    fresh = verification.verify_project_sql_plan(
        changed, *roots, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert fresh.verified
    assert inspect_project_sql_plan(fresh).fixed_envelope is copied


def test_no_literal_fallback_or_missing_representation_requirements(products):
    roots, plan, checked, _ = products[0]
    original = next(
        e for e in plan.expressions if type(e) is row.ProjectSQLBoundLiteral
    )
    restored = row.ProjectSQLLiteral(
        ref=original.ref,
        site=original.site,
        expression=original.expression,
        value_type=original.value_type,
    )
    _rejected(
        roots,
        plan,
        _graft(plan, expressions=_tuple_replaced(plan.expressions, original, restored)),
    )
    for changes in (
        {
            "demands": tuple(
                d
                for d in plan.demands
                if not isinstance(d, literal.ProjectSQLLiteralDemand)
            )
        },
        {"demands": (*plan.demands[:-1], _graft(plan.demands[-1], contexts=()))},
        {"demands": (*plan.demands[:-1], _graft(plan.demands[-1], requirements=()))},
        {"origins": plan.origins[:-1]},
    ):
        bad = _graft(plan, **changes)
        assert not verification.verify_project_sql_plan(
            bad, *roots, literal_policy=P.BIND_SAFE_LITERALS
        ).verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(_graft(checked, plan=bad))


def test_unknown_extraction_evidence_preserves_without_forging_plan_evidence(products):
    _, plan, _, _ = products[0]
    position = plan.literal_slots[0].site.position
    assert (
        literal.classify(_graft(position, value_type=None), P.BIND_SAFE_LITERALS)
        is Why.TYPE_UNAVAILABLE
    )
    assert (
        literal.classify(_graft(position, role=R.UNKNOWN), P.BIND_SAFE_LITERALS)
        is Why.UNKNOWN_CONTEXT
    )
    value_type = position.value_type
    assert value_type is not None
    for changed in (
        replace(value_type, kind=ValueTypeKind.UNKNOWN),
        replace(
            value_type,
            resolved_type=replace(value_type.resolved_type, kind=TypeKind.TYPE_ALIAS),
        ),
    ):
        expected = (
            Why.TYPE_UNAVAILABLE
            if changed.kind is ValueTypeKind.UNKNOWN
            else Why.NON_BUILTIN
        )
        assert (
            literal.classify(_graft(position, value_type=changed), P.BIND_SAFE_LITERALS)
            is expected
        )
    # These are extraction-adapter controls using real retained positions, not
    # claims that deleting mandatory scalar facts produces a valid whole plan.
    assert verification.verify_fixed_literal_envelope(
        plan, plan.fixed_envelope, literal_policy=P.BIND_SAFE_LITERALS
    )


@pytest.mark.parametrize("alias", (False, True))
def test_consumed_type_arguments_are_structural_source_positions(tmp_path, alias):
    source = _source("    select:\n        key\n").replace(
        "key: Int nullable",
        "key: Money nullable" if alias else "key: Decimal(12, 2) nullable",
    )
    if alias:
        source = "type Money = Decimal(12, 2)\n" + source
    source = "shape Unused:\n    other: Decimal(18, 4)\n" + source
    _, plan, _, _ = _product(tmp_path, source)
    sites = [s for s in plan.literal_sites if s.position.role is R.TYPE]
    assert [s.position.literal.value for s in sites] == [12, 2]
    assert all(
        s.reason is Why.SPECIALIZED
        and s.position.expression is None
        and s.position.value_type is None
        for s in sites
    )
    assert all(
        s.position.owner.definition.name == ("Money" if alias else "Row") for s in sites
    )
    assert plan.literal_slots == ()
    bad = _graft(
        plan, literal_sites=tuple(s for s in plan.literal_sites if s not in sites)
    )
    assert not verification.verify_fixed_literal_envelope(
        bad, bad.fixed_envelope, literal_policy=P.BIND_SAFE_LITERALS
    )


def test_literal_traversal_materializes_only_real_leaf_ancestries(products):
    _, plan, _, _ = products[0]
    leaf = plan.literal_slots[0].site.position.literal
    expression = leaf
    for _ in range(1500):
        expression = UnaryExpr(span=leaf.span, operator="+", operand=expression)
    ((actual, ancestry),) = tuple(literal.literal_nodes(expression))
    assert actual is leaf and len(ancestry) == 1500
    assert ancestry[0][0] is expression and all(
        type(i) is int and i == 0 for _, i in ancestry
    )


def test_all_literal_inventories_cannot_be_erased_together(products):
    roots, plan, _, _ = products[0]
    witnesses = (
        literal.ProjectSQLLiteralSite,
        literal.ProjectSQLLiteralSlot,
        literal.ProjectSQLFixedLiteralValue,
        literal.ProjectSQLBindUse,
    )
    bad = _graft(
        plan,
        literal_sites=(),
        literal_slots=(),
        bind_uses=(),
        fixed_envelope=_graft(plan.fixed_envelope, slots=(), values=()),
        demands=tuple(
            d
            for d in plan.demands
            if not isinstance(d, literal.ProjectSQLLiteralDemand)
        ),
        origins=tuple(o for o in plan.origins if not isinstance(o.evidence, witnesses)),
    )
    _rejected(roots, plan, bad)


def test_standalone_envelope_requires_exact_binding_scope(products):
    _, plan, _, _ = products[0]
    bad = _graft(plan, bindings=_graft(plan.bindings, scope=products[1][1].scope))
    assert not verification.verify_fixed_literal_envelope(
        bad, bad.fixed_envelope, literal_policy=P.BIND_SAFE_LITERALS
    )


def test_missing_envelope_and_uninitialized_plan_are_normalized_rejections(products):
    roots, _, checked, _ = products[0]
    bad = object.__new__(planner.ProjectSQLPlan)
    assert not verification.verify_project_sql_plan(
        bad, *roots, literal_policy=P.BIND_SAFE_LITERALS
    ).verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(_graft(checked, plan=bad))


@pytest.mark.parametrize(
    "what",
    (
        "slot_type",
        "slot_tag",
        "slot_site",
        "slot_scope",
        "use_slot",
        "use_expression",
        "use_role",
    ),
)
def test_exact_slot_and_actual_use_associations(products, what):
    roots, plan, _, _ = products[0]
    slot, use = plan.literal_slots[0], plan.bind_uses[0]
    slots = {
        "slot_type": _graft(slot, value_type=replace(slot.value_type)),
        "slot_tag": _graft(slot, tag=literal.ProjectSQLLiteralTag.TEXT),
        "slot_site": _graft(slot, site=plan.literal_slots[1].site),
        "slot_scope": _graft(slot, ref=_graft(slot.ref, scope=products[1][1].scope)),
    }
    uses = {
        "use_slot": _graft(use, slot=plan.literal_slots[1]),
        "use_expression": _graft(use, expression=plan.bind_uses[1].expression),
        "use_role": _graft(
            use, ref=_graft(use.ref, kind=planner.ProjectSQLPlanRefKind.EXPRESSION)
        ),
    }
    bad = (
        _graft(plan, literal_slots=(slots[what], *plan.literal_slots[1:]))
        if what in slots
        else _graft(plan, bind_uses=(uses[what], *plan.bind_uses[1:]))
    )
    _rejected(roots, plan, bad)


@pytest.mark.parametrize("payload", ([1], {"value": 1}, (1,), "1"))
def test_payload_shapes_are_closed_primitives(products, payload):
    roots, plan, _, _ = products[0]
    values = plan.fixed_envelope.values
    bad = _graft(
        plan,
        fixed_envelope=_graft(
            plan.fixed_envelope, values=(_graft(values[0], value=payload), *values[1:])
        ),
    )
    _rejected(roots, plan, bad)


def test_rebuilt_order_is_deterministic_but_snapshot_refs_are_local(products):
    roots, original, _, _ = products[0]
    other = planner.build_project_sql_plan(*roots, literal_policy=P.BIND_SAFE_LITERALS)
    assert isinstance(other, planner.ProjectSQLPlan)
    assert verification.verify_project_sql_plan(
        other, *roots, literal_policy=P.BIND_SAFE_LITERALS
    ).verified
    for left, right in zip(original.literal_slots, other.literal_slots, strict=True):
        assert left.ref.position == right.ref.position and left.ref is not right.ref
        assert left.site.position.literal is right.site.position.literal
        assert left.site.position.owner is right.site.position.owner
        assert left.site.position.context is not right.site.position.context
    assert original.scope is not other.scope


def test_exact_refs_and_immutable_source_bearing_inspection(products):
    _, plan, _, view = products[0]
    foreign = products[1][1]
    for ref in (
        plan.literal_sites[0].ref,
        foreign.literal_slots[0].ref,
        plan.exports[0].ref,
    ):
        with pytest.raises(ValueError):
            view.fixed_value(ref)
    with pytest.raises(ValueError):
        view.literal_site(plan.literal_slots[0].ref)
    with pytest.raises(ValueError):
        view.literal_value(plan.literal_slots[0].ref)
    with pytest.raises(ValueError):
        view.literal_value(
            next(e.ref for e in plan.expressions if isinstance(e, row.ProjectSQLUnary))
        )
    for value in (
        plan.fixed_envelope,
        *plan.literal_sites,
        *plan.literal_slots,
        *plan.bind_uses,
        *plan.fixed_envelope.values,
    ):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(value, "ref", None)


def test_verification_and_inspection_never_allocate_classify_or_infer(
    products, monkeypatch
):
    roots, plan, checked, _ = products[0]

    def forbidden(*args, **kwargs):
        pytest.fail("Verification called a producer or eligibility classifier")

    names = (
        "infer_row_expression",
        "resolve_named_window_namespace",
        "analyze_window_expression",
        "build_project_sql_plan",
        "build_project_sql_bindings",
        "build_project_query_block_ir",
        "build_project_completed_semantic_result",
    )
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pietto.") and module is not None:
            for member in names:
                if hasattr(module, member):
                    monkeypatch.setattr(module, member, forbidden)
    for module, member in (
        (literal, "classify"),
        (literal, "build"),
        (row, "scalar_nodes"),
        (row, "scalar_children"),
    ):
        monkeypatch.setattr(module, member, forbidden)
    assert verification.verify_fixed_literal_envelope(
        plan, plan.fixed_envelope, literal_policy=P.BIND_SAFE_LITERALS
    )
    assert verification.verify_project_sql_plan(
        plan, *roots, literal_policy=P.BIND_SAFE_LITERALS
    ).verified
    assert inspect_project_sql_plan(checked).literal_slots is plan.literal_slots


@pytest.mark.parametrize(
    "body,code",
    (
        ("    select:\n        x = null\n", "PIE-S2333"),
        ('    select:\n        x = trim("hello")\n', "call_authority_unavailable"),
    ),
)
def test_unsupported_prerequisites_are_not_preserved_transport_success(
    tmp_path, body, code
):
    roots = _roots(tmp_path, _source(body))
    for policy in P:
        plan = planner.build_project_sql_plan(*roots, literal_policy=policy)
        assert isinstance(plan, planner.ProjectSQLPlanUnavailable)
        if code.startswith("PIE-"):
            assert not roots[0].ok and code in [d.code for d in roots[0].diagnostics]
        else:
            assert roots[0].ok and code in [b.kind.value for b in plan.blockers]
