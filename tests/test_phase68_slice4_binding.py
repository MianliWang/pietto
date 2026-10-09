"""Full eligible literal domains and independent binding correspondence."""

from dataclasses import replace

import pytest

from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_sql_plan import ProjectSQLPlan

from _pietto_phase68_slice4_probe import template
import _pietto_phase67_result_product_probe as product
from pietto._project import project_execution_template as binding
from pietto._project import project_execution_binding_verification as checking
from pietto._project import project_sql_emission_parameters as parameters


def bind(t, *values):
    return binding.bind_values(t, tuple(zip(t.slots, values, strict=True)))


@pytest.fixture(scope="module")
def predicate(tmp_path_factory):
    return template(tmp_path_factory.mktemp("s04-predicate"))


def test_reusable_immutable_a_b_a_and_failed_bind(predicate):
    t = predicate
    supplied = [[t.slots[0], 9007199254740993]]
    a = binding.bind_values(t, supplied)
    supplied[0][1] = -7
    supplied.clear()
    b = bind(t, -1)
    assert a.values == a.arguments == (9007199254740993,)
    assert b.values == b.arguments == (-1,)
    assert t.slots[0].original.site.position.literal.value == 1
    assert a.artifact is not b.artifact
    with pytest.raises(binding.BindingError, match="^BINDING_VALUE:0:Int$"):
        bind(t, True)
    for item in (a, b, a):
        checking.verify_binding(item)
    assert "9007199254740993" not in repr(a)


@pytest.mark.parametrize(
    "value", [True, None, 1.0, "1", 2**63, -(2**63) - 1, [], object()]
)
def test_strict_int_rejection(predicate, value):
    with pytest.raises(binding.BindingError, match="^BINDING_VALUE:0:Int$"):
        bind(predicate, value)


def test_exact_inventory(predicate, tmp_path):
    other = template(tmp_path / "foreign")
    slot = predicate.slots[0]
    for pairs in (
        (),
        ((slot, 2), (slot, 2)),
        ((other.slots[0], 2),),
        ((replace(slot), 2),),
        {slot: 2},
    ):
        with pytest.raises(binding.BindingError, match="^BINDING_SLOTS$"):
            binding.bind_values(predicate, pairs)


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize(
    "seed,values,bad",
    [
        ("true", (False, True), (0, 1, None, "false")),
        ("1.5", (0.0, -0.0, 1.25), (1, True, float("inf"), float("nan"), None)),
        ('"seed"', ("", "雪é😀  ? %s $1", "x" * 1024), (b"x", None, "\ud800")),
    ],
)
def test_complete_eligible_domains(tmp_path, target, seed, values, bad):
    source = product.source(target).replace("renamed = id", "renamed = " + seed)
    t = template(tmp_path, source, target=target)
    for value in values:
        b = bind(t, value)
        checking.verify_binding(b)
        assert checking.atom(b.arguments[0]) == checking.atom(
            int(value) if target == "mysql" and type(value) is bool else value
        )
        if type(value) is str:
            original = b.artifact.parameter_uses[0].original
            real = parameters.representation(
                parameters.build_value(
                    b.artifact.request.plan,
                    original.ref,
                    target,
                    {u.original.ref: u for u in b.artifact.parameter_uses},
                ),
                target,
            )
            assert real["domain"]["max_characters"] == len(value)
    for value in bad:
        with pytest.raises(
            binding.BindingError, match="^BINDING_VALUE:0:%s$" % t.slots[0].tag
        ):
            bind(t, value)
    if seed == '"seed"':
        if target == "postgres":
            with pytest.raises(binding.BindingError, match="^BINDING_VALUE:0:Text$"):
                bind(t, "x\0y")
        else:
            assert bind(t, "x\0y").arguments == ("x\0y",)


def test_equal_distinct_slots_and_repeated_native_use(tmp_path):
    source = product.source("postgres").replace(
        "    select:", "    where id > 1 and other > 1\n    select:"
    )
    t = template(tmp_path, source)
    assert len(t.slots) == 2 and t.slots[0] is not t.slots[1]
    accepted = bind(t, 2, 3)
    assert accepted.arguments == (2, 3)
    with pytest.raises(binding.BindingError, match="^BINDING_SLOTS$"):
        binding.bind_values(t, ((t.slots[1], 2), (t.slots[0], 3)))
    leaves = [u.original for u in accepted.artifact.parameter_uses]
    occurrences = tuple((leaf, "pg_int8") for leaf in (leaves[0], leaves[0], leaves[1]))
    pg = parameters.allocate_uses("postgres", occurrences, 3)
    my = parameters.allocate_uses(
        "mysql", tuple((leaf, "my_signed_int") for leaf, _ in occurrences), 3
    )
    assert tuple(u.server_index for u in pg) == (1, 1, 2)
    assert tuple(u.server_index for u in my) == (1, 2, 3)
    # Pure mapping witness, not an invented emitted SQL/native repetition.
    for uses, family, expected in ((pg, "postgres", (2, 3)), (my, "mysql", (2, 2, 3))):
        from types import SimpleNamespace

        image = SimpleNamespace(
            request=SimpleNamespace(plan=accepted.artifact.request.plan, family=family),
            parameter_uses=uses,
        )
        assert checking.native_arguments(image, accepted.values) == expected


def test_coordinated_values_arguments_and_old_artifact(predicate):
    a, b = bind(predicate, 2), bind(predicate, 3)
    for damaged, code in (
        (replace(a, values=(3,), arguments=(3,)), "LITERAL"),
        (replace(a, artifact=b.artifact), "LITERAL"),
        (replace(a, arguments=()), "STATE"),
        (replace(a, arguments=(True,)), "STATE"),
        (replace(a, template=replace(predicate)), "STATE"),
    ):
        with pytest.raises(binding.BindingError, match="^BINDING_%s$" % code):
            checking.verify_binding(damaged)
    # Even copying a superficially matching state does not change syntax evidence.
    damaged = replace(a, values=(3,), arguments=(3,))
    damaged = replace(damaged, _state=checking.binding_state(damaged))
    with pytest.raises(binding.BindingError, match="^BINDING_LITERAL$"):
        checking.verify_binding(damaged)


def test_signed_zero_is_not_python_equality(tmp_path):
    t = template(
        tmp_path, product.source("postgres").replace("renamed = id", "renamed = 1.0")
    )
    positive, negative = bind(t, 0.0), bind(t, -0.0)
    assert positive.arguments == negative.arguments
    assert checking.binding_state(positive) != checking.binding_state(negative)
    damaged = replace(positive, values=(-0.0,), arguments=(-0.0,))
    damaged = replace(damaged, _state=checking.binding_state(damaged))
    with pytest.raises(binding.BindingError, match="^BINDING_LITERAL$"):
        checking.verify_binding(damaged)


def test_value_dependent_arithmetic_and_sign(tmp_path):
    source = product.source("postgres").replace("renamed = id", "renamed = id + 1")
    t = template(tmp_path / "arithmetic", source, lower=0, upper=10)
    assert bind(t, 2).arguments == (2,)
    with pytest.raises(binding.BindingError, match="^BINDING_INVALID$"):
        bind(t, 2**63 - 1)
    signed = template(
        tmp_path / "signed",
        product.source("postgres").replace("renamed = id", "renamed = -1"),
    )
    assert bind(signed, 9007199254740993).arguments == (9007199254740993,)
    with pytest.raises(binding.BindingError, match="^BINDING_INVALID$"):
        bind(signed, -(2**63))


def test_parameterless_keeps_owned_original(tmp_path):
    t = template(tmp_path, product.source("postgres"))
    b = bind(t)
    assert b.artifact is t.artifact and b.values == b.arguments == ()


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize(
    "case,variant",
    [
        ("R_fixed_direct", "table_bind"),
        ("R_fixed_direct", "query_bind"),
        ("S_fixed_named", "named_bind"),
        ("S_fixed_named", "imported_bind"),
        ("T_row_direct", "query_bind"),
        ("U_row_named", "imported_bind"),
    ],
)
def test_existing_fixed_site_closure(tmp_path, target, case, variant):
    import _pietto_phase66_sql_emission_probe as probe
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    before = serialize_project_sql_emission(outcome)
    t = binding.prepare_template(outcome.artifact)
    values = tuple(v.value for v in outcome.artifact.fixed_values)
    accepted = bind(t, *values)
    checking.verify_binding(accepted)
    assert len(accepted.artifact.parameter_uses) == len(outcome.artifact.parameter_uses)
    assert serialize_project_sql_emission(outcome) == before
    assert accepted.arguments == probe.decoded_arguments(probe.decode_public(before))


def test_structural_limit_and_original_context_are_not_slots(tmp_path):
    source = (
        product.source("postgres").replace(
            "    select:", "    where id > 1\n    select:"
        )
        + "    order by:\n        id desc\n    limit 2\n"
    )
    t = template(tmp_path, source)
    assert len(t.slots) == 1 and t.slots[0].original.site.position.role.value == "where"
    accepted = bind(t, 7)
    assert b" LIMIT 2" in accepted.artifact.rendered.sql
    assert b" ORDER BY " in accepted.artifact.rendered.sql
    with pytest.raises(binding.BindingError, match="^BINDING_SLOTS$"):
        binding.bind_values(t, ((t.slots[0], 7), ("limit", 3)))
    sites = t.artifact.request.plan.literal_sites
    limit = next(s.position.literal for s in sites if s.position.role.value == "limit")
    # The original graph is never mutated by production. This adversarial test
    # substitutes a structural value and restores its own fixture afterwards.
    original = limit.value
    assert type(original) is int
    try:
        object.__setattr__(limit, "value", original + 1)
        with pytest.raises(binding.BindingError, match="^BINDING_ARTIFACT$"):
            checking.verify_binding(accepted)
    finally:
        object.__setattr__(limit, "value", original)
    checking.verify_binding(accepted)
    with pytest.raises(binding.BindingError, match="^BINDING_INVENTORY$"):
        checking.verify_template(replace(t, artifact=accepted.artifact))


def test_native_use_order_count_and_anchors_are_verified(tmp_path):
    source = product.source("postgres").replace(
        "    select:", "    where id > 1 and other > 2\n    select:"
    )
    accepted = bind(template(tmp_path, source), 3, 4)
    uses = accepted.artifact.parameter_uses
    for wrong in (
        uses[::-1],
        uses[:1],
        (replace(uses[0], server_index=2), uses[1]),
        (replace(uses[0], physical_type="pg_text"), uses[1]),
    ):
        with pytest.raises(binding.BindingError, match="^BINDING_ARTIFACT$"):
            checking.verify_binding(
                replace(
                    accepted, artifact=replace(accepted.artifact, parameter_uses=wrong)
                )
            )


def _proof_artifact(directory, *, proved=True, retained=False):
    import _pietto_phase66_sql_emission_probe as probe
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import (
        ProjectSingleMatchRequest,
        ProjectSingleMatchAssessment,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_emission import emit_project_sql

    source = """table ranked:
    from rhs
    select:
        id
    limit 1
query result:
    from lhs
    inner join ranked as r:
        from lhs
        on lhs.id == r.id and lhs.id > 1
    select:
        value = lhs.id
"""
    if retained:
        source += "query unused:" + source.split("query result:", 1)[1]
    if not proved:
        source = source.replace("    limit 1\n", "")
    item = probe.join_witness("postgres", source, policy="bind_safe_literals")
    checked, _ = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    completed = checked.completed
    requests = []
    for condition in completed.roots.join_conditions.entries:
        request = ProjectSingleMatchRequest(
            owner=condition.use.owner, use=condition.use, condition=condition
        )
        assessment = ProjectSingleMatchAssessment(
            root=completed.effective_outputs, request=request
        )
        requests.append(replace(request, input_pairs=assessment.input_pairs))
    completed = with_project_single_match_requests(completed, tuple(requests))
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    (selected,) = tuple(o for o in ir.owners if o.definition.name == "result")
    policy = checked.literal_policy
    plan = build_project_sql_plan(completed, bundle, selected, literal_policy=policy)
    checked = verify_project_sql_plan(
        plan, completed, bundle, selected, literal_policy=policy
    )
    return emit_project_sql(checked, item["contract"].encode())


def test_proofs_rederived_and_unfulfilled_guard_refuses(tmp_path):
    outcome = _proof_artifact(tmp_path / "proved")
    assert outcome.status == "VERIFIED", outcome
    assert outcome.artifact is not None
    t = binding.prepare_template(outcome.artifact)
    accepted = bind(t, 2)
    before = outcome.artifact.request.verification.completed
    after = accepted.artifact.request.verification.completed
    assert len(after.single_match_requests) == 1
    assert (
        after.single_matches.entries[0].proofs[0]
        is not before.single_matches.entries[0].proofs[0]
    )
    assert (
        after.single_matches.entries[0].proofs[0].kind
        == before.single_matches.entries[0].proofs[0].kind
    )
    rejected = _proof_artifact(tmp_path / "unproved", proved=False)
    assert rejected.artifact is None
    assert any(
        b.detail == "original_enforcement_not_fulfilled" for b in rejected.blockers
    )
    with pytest.raises(binding.BindingError, match="^BINDING_ARTIFACT$"):
        binding.prepare_template(rejected.artifact)


@pytest.mark.parametrize("all_unique", [False, True])
def test_complete_path_and_hop_request_correspondence(tmp_path, all_unique):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots,
        _path_source,
        _path_requests,
    )
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
    )
    from pietto._project.project_single_match import ProjectSingleMatchScope

    original, _, _ = _roots(
        tmp_path, _path_source(all_unique=all_unique), _path_requests
    )
    # Semantic-layer witness includes the unfulfilled whole-path request; such
    # a graph cannot produce executable emission before S07 fulfills its guard.
    attribution = original.semantic_result.module_attribution_facts
    assert attribution is not None
    parsed = attribution._authority.parse_result
    image, nodes = binding._syntax_image(parsed, {})
    fresh = build_project_completed_semantic_result(
        build_empty_project_semantic_result(image)
    )
    assert type(fresh) is ProjectConcreteCompletedSemanticResult
    mapped = binding._requests(original, fresh, nodes)
    checking._obligations(original, mapped, nodes)
    assert tuple(r.scope for r in mapped.single_match_requests) == (
        ProjectSingleMatchScope.PATH_HOP,
        ProjectSingleMatchScope.PATH_HOP,
        ProjectSingleMatchScope.WHOLE_PATH,
    )
    assert tuple(a.state for a in mapped.single_matches.entries) == tuple(
        a.state for a in original.single_matches.entries
    )
    wrong = replace(
        mapped.single_match_requests[0], hop=mapped.single_match_requests[1].hop
    )
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )

    swapped = with_project_single_match_requests(
        fresh, (wrong, *mapped.single_match_requests[1:])
    )
    with pytest.raises(binding.BindingError, match="^BINDING_OBLIGATIONS$"):
        checking._obligations(original, swapped, nodes)


def test_repeated_request_object_retains_alias_and_cardinality(tmp_path):
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
        build_project_completed_semantic_result,
    )
    from pietto._project.model import build_empty_project_semantic_result

    outcome = _proof_artifact(tmp_path)
    assert outcome.artifact is not None
    original = outcome.artifact.request.verification.completed
    (request,) = original.single_match_requests
    original = with_project_single_match_requests(original, (request, request))
    attribution = original.semantic_result.module_attribution_facts
    assert attribution is not None
    parsed = attribution._authority.parse_result
    image, nodes = binding._syntax_image(parsed, {})
    fresh = build_project_completed_semantic_result(
        build_empty_project_semantic_result(image)
    )
    assert type(fresh) is ProjectConcreteCompletedSemanticResult
    mapped = binding._requests(original, fresh, nodes)
    assert len(mapped.single_match_requests) == 2
    assert mapped.single_match_requests[0] is mapped.single_match_requests[1]
    checking._obligations(original, mapped, nodes)
    split = with_project_single_match_requests(
        fresh,
        (mapped.single_match_requests[0], replace(mapped.single_match_requests[1])),
    )
    with pytest.raises(binding.BindingError, match="^BINDING_OBLIGATION_ALIAS$"):
        checking._obligations(original, split, nodes)


@pytest.mark.parametrize(
    "case,variant,role",
    [
        ("A_window_navigation", "offsets", "window_argument"),
        ("A_window_frame", "rows", "frame"),
    ],
)
def test_window_static_arguments_and_frames_do_not_become_slots(
    tmp_path, case, variant, role
):
    import json
    import _pietto_phase66_sql_emission_probe as probe

    item = probe.fixture("postgres", case, variant)
    contract = json.loads(item["contract"])
    contract["environment"].append(
        dict(key="parameter_protocol", scope="statement", value="postgres_extended")
    )
    source = item["source"].replace("    select:", "    where id > 1\n    select:")
    checked, outcome = probe.build_case(
        tmp_path, source, json.dumps(contract), "bind_safe_literals"
    )
    assert outcome.status == "VERIFIED", outcome
    assert outcome.artifact is not None
    t = binding.prepare_template(outcome.artifact)
    assert all(s.original.site.position.role.value == "where" for s in t.slots)
    assert type(checked.plan) is ProjectSQLPlan
    assert any(s.position.role.value == role for s in checked.plan.literal_sites)
    accepted = bind(t, 2)
    checking.verify_binding(accepted)
    static = tuple(
        s
        for s in accepted.artifact.request.plan.literal_sites
        if s.position.role.value == role
    )
    assert static and all(
        s.disposition.value == "preserved_with_reason" for s in static
    )
    with pytest.raises(binding.BindingError, match="^BINDING_SLOTS$"):
        binding.bind_values(t, (*tuple((s, 2) for s in t.slots), (static[0], 2)))


def test_unselected_retained_request_is_not_dropped(tmp_path):
    outcome = _proof_artifact(tmp_path, retained=True)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    t = binding.prepare_template(outcome.artifact)
    accepted = bind(t, 2)
    before = t.artifact.request.verification.completed
    after = accepted.artifact.request.verification.completed
    assert len(before.single_match_requests) == len(after.single_match_requests) == 2
    assert tuple(r.owner.definition.name for r in after.single_match_requests) == (
        "result",
        "unused",
    )
    checking.verify_binding(accepted)
