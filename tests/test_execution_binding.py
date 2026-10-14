"""Full eligible literal domains and independent binding correspondence."""

from dataclasses import replace
import json

import pytest

from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_sql_plan import ProjectSQLPlan

from _pietto_execution_binding import bind, proof_artifact, template
import _pietto_results_product as product
import _pietto_sql_emission as probe
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project import project_execution_template as binding
from pietto._project import project_execution_binding_verification as checking
from pietto._project import project_sql_emission_parameters as parameters


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
    import _pietto_sql_emission as emission

    source = product.source("postgres").replace("renamed = id", "renamed = id + 1")
    document = json.loads(product.emission_input("postgres", lower=0, upper=10))
    document["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "pg_int4"
    }
    document["environment"] += [
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"},
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        },
    ]
    _, outcome = emission.build_case(
        tmp_path / "arithmetic", source, json.dumps(document), "bind_safe_literals"
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    t = binding.prepare_template(outcome.artifact)
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
    import _pietto_sql_emission as probe
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


def test_proofs_rederived_and_unfulfilled_guard_refuses(tmp_path):
    outcome = proof_artifact(tmp_path / "proved")
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
    rejected = proof_artifact(tmp_path / "unproved", proved=False)
    assert rejected.artifact is None
    assert any(
        b.detail == "original_enforcement_not_fulfilled" for b in rejected.blockers
    )
    with pytest.raises(binding.BindingError, match="^BINDING_ARTIFACT$"):
        binding.prepare_template(rejected.artifact)


@pytest.mark.parametrize("all_unique", [False, True])
def test_complete_path_and_hop_request_correspondence(tmp_path, all_unique):
    from _pietto_plan_joins import _roots, _path_source, _path_requests
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

    outcome = proof_artifact(tmp_path)
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
    import _pietto_sql_emission as probe

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
    outcome = proof_artifact(tmp_path, retained=True)
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


def _witness(directory, target, variant):
    """The published v2 conformance query: its compiled template and its
    independently decoded public document."""
    item = probe.fixture(target, "Q_query_parameters", variant)
    _, outcome = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    return binding.prepare_live_template(outcome.artifact), document


def _parameterized(directory, target, variant):
    """The compiled template of the published v2 conformance query."""
    return _witness(directory, target, variant)[0]


def _named(t, *values):
    return tuple(zip(t.parameters, values, strict=True))


def _literals(t):
    return tuple((s, s.original.site.position.literal.value) for s in t.slots)


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize("variant", ["preserve", "bind"])
def test_a_parameter_binding_rederives_the_template_statement(
    tmp_path, target, variant
):
    t = _parameterized(tmp_path, target, variant)
    assert [(p.name, p.tag, p.nullable) for p in t.parameters] == [
        ("low", "Int", False),
        ("label", "Text", True),
    ]
    a = binding.bind_values(t, _literals(t), _named(t, 10, "x"))
    b = binding.bind_values(t, _literals(t), _named(t, -5, None))
    for item in (a, b, a):
        checking.verify_binding(item)
        # Every binding re-derives its facts; the statement bytes never change.
        assert item.artifact is not t.artifact
        assert item.artifact.rendered.sql == t.artifact.rendered.sql
    header = a.artifact.request.plan.parameters
    low = [u for u in a.artifact.parameter_uses if u.parameter is header[0]]
    if target == "postgres":
        # One `$n` per owner: every read of `low` reuses its first index.
        assert {u.server_index for u in low} == {1}
        assert len(a.arguments) == len(t.slots) + 2
    else:
        assert len(a.arguments) == len(a.artifact.parameter_uses) > len(t.slots) + 2
    assert a.arguments.count(10) == (len(low) if target == "mysql" else 1)
    assert None in b.arguments and "x" in a.arguments
    assert a.parameters == (10, "x") and b.parameters == (-5, None)


@pytest.mark.parametrize(
    ("values", "detail"),
    [
        ((True, "x"), "BINDING_PARAMETER:0:Int"),
        ((None, "x"), "BINDING_PARAMETER:0:Int"),
        ((2**63, "x"), "BINDING_PARAMETER:0:Int"),
        ((1, 1), "BINDING_PARAMETER:1:Text"),
        ((1, "\0"), "BINDING_PARAMETER:1:Text"),
        # `above = low + 1` defers its range check to every binding.
        ((2**63 - 1, "x"), "BINDING_INVALID"),
    ],
)
def test_a_parameter_value_is_checked_by_its_binding(tmp_path, values, detail):
    t = _parameterized(tmp_path, "postgres", "preserve")
    with pytest.raises(binding.BindingError, match="^%s$" % detail):
        binding.bind_values(t, (), _named(t, *values))


def test_the_header_is_bound_completely_by_its_own_parameters(tmp_path):
    t = _parameterized(tmp_path, "postgres", "preserve")
    other = _parameterized(tmp_path / "other", "postgres", "preserve")
    low, label = t.parameters
    for named in (
        None,
        (),
        ((low, 1),),
        ((label, "x"), (low, 1)),
        ((low, 1), (label, "x"), (label, "x")),
        ((other.parameters[0], 1), (label, "x")),
        ((replace(low), 1), (label, "x")),
        {low: 1, label: "x"},
    ):
        with pytest.raises(binding.BindingError, match="^BINDING_PARAMETERS$"):
            binding.bind_values(t, (), named)


def test_an_unregistered_binding_obligation_kind_never_binds(tmp_path, monkeypatch):
    t = _parameterized(tmp_path, "postgres", "preserve")
    accepted = binding.bind_values(t, (), _named(t, 1, "x"))
    monkeypatch.setattr(checking, "BINDING_CHECKS", {})
    # The binder reports any refusal of its own result as an invalid binding.
    with pytest.raises(binding.BindingError, match="^BINDING_INVALID$"):
        binding.bind_values(t, (), _named(t, 1, "x"))
    with pytest.raises(binding.BindingError, match="^BINDING_OBLIGATION_KIND$"):
        checking.verify_binding(accepted)


def test_a_forged_parameter_binding_is_refused(tmp_path):
    t = _parameterized(tmp_path, "postgres", "preserve")
    accepted = binding.bind_values(t, (), _named(t, 1, "x"))
    other = binding.bind_values(t, (), _named(t, 2, "x"))
    for forged in (
        replace(accepted, parameters=(2, "x")),
        replace(accepted, arguments=other.arguments),
        replace(accepted, artifact=other.artifact),
        replace(accepted, artifact=t.artifact),
    ):
        with pytest.raises(binding.BindingError):
            checking.verify_binding(forged)
    # A verified statement of another template never stands in for this one.
    bound = _parameterized(tmp_path / "bound", "postgres", "bind")
    foreign = binding.bind_values(bound, _literals(bound), _named(bound, 1, "x"))
    with pytest.raises(binding.BindingError, match="^BINDING_TEMPLATE_BYTES$"):
        checking.verify_binding(replace(accepted, artifact=foreign.artifact))


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize("variant", sorted(probe.PARAMETER_POSITION_VARIANTS))
def test_each_position_witness_binds_to_its_decoded_arguments(
    tmp_path, target, variant
):
    """A result or post-aggregation witness binds through the product binder,
    which re-derives every obligation, and sends exactly the arguments the
    conformance runner decodes for it."""
    t, document = _witness(tmp_path, target, variant)
    values = probe.bindings("Q_query_parameters", variant)
    assert values is not None
    accepted = binding.bind_values(
        t, _literals(t), _named(t, *(values[p.name] for p in t.parameters))
    )
    checking.verify_binding(accepted)
    assert accepted.artifact.rendered.sql == t.artifact.rendered.sql
    assert accepted.arguments == probe.decoded_arguments(document, values)


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize(
    ("variant", "values"),
    [
        # `id` proves over its whole int8 carrier: id * 2 and id + 1 leave it.
        ("grouped_null_high", {"low": 2, "high": None}),
        ("grouped_value_high", {"low": 1, "high": 1}),
        ("result_contains_a", {"low": -1, "label": "a"}),
        # `id * low` and `low + 1` both leave int8 here.
        ("result_null_label", {"low": 2**63 - 1, "label": None}),
    ],
)
def test_a_position_binding_outside_its_proven_range_is_refused(
    tmp_path, target, variant, values
):
    t, _ = _witness(tmp_path, target, variant)
    with pytest.raises(binding.BindingError, match="^BINDING_INVALID$"):
        binding.bind_values(
            t, _literals(t), _named(t, *(values[p.name] for p in t.parameters))
        )


QUALIFY_ONLY = """query result(low: Int not null, label: Text nullable):
    from rows
    where contains(text, label)
    select:
        id
        r = row_number() window:
            order by:
                id
    qualify:
        r <= low + 1
"""


@pytest.mark.parametrize("target", ["postgres", "mysql"])
def test_the_qualify_obligation_alone_refuses_its_overflowing_binding(tmp_path, target):
    """QUALIFY `r <= low + 1` is this body's only Int obligation, so only the
    predicate-stage range refuses the int8 top."""
    item = probe.parameterized_fixture(target, QUALIFY_ONLY)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    t = binding.prepare_live_template(outcome.artifact)
    checking.verify_binding(binding.bind_values(t, (), _named(t, 2**63 - 2, None)))
    with pytest.raises(binding.BindingError, match="^BINDING_INVALID$"):
        binding.bind_values(t, (), _named(t, 2**63 - 1, None))


# The S04r positions the conformance witnesses leave out, each compiled and
# bound through the product binder: the closed builtin value arguments, a
# DISTINCT ORDER key's constant leaf, MIN over a dependent LET and SATISFYING
# over a JOIN.
COMPILED_POSITIONS = {
    "builtins_distinct": (
        """query result(low: Int not null, label: Text nullable):
    from rows
    where starts_with(label, text) or ends_with(label, text) or label is null
    select distinct:
        id
        b = upper(label)
        c = trim(label)
        d = coalesce(label, text)
        e = nullif(label, text)
        g = coalesce(low, id)
        h = sign(low)
        s = id + low
    order by:
        id + low
""",
        {"low": 0, "label": "x"},
    ),
    "let_min": (
        """query result(low: Int not null, high: Int nullable):
    from rows
    let:
        s = id + high
        k = id * low
    group by:
        k
    select:
        k
        lo = min(s)
""",
        {"low": 1, "high": None},
    ),
    "joined_satisfying": (
        """query result(low: Int not null):
    from rows
    inner join rows as r:
        from rows
        on rows.id == r.id
    group by:
        rows.id
    select:
        k = rows.id
        n = count()
    satisfying:
        n > low
""",
        {"low": 1},
    ),
}


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize("name", sorted(COMPILED_POSITIONS))
def test_every_result_position_compiles_and_binds(tmp_path, target, name):
    body, values = COMPILED_POSITIONS[name]
    item = probe.parameterized_fixture(target, body)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    t = binding.prepare_live_template(outcome.artifact)
    accepted = binding.bind_values(
        t, _literals(t), _named(t, *(values[p.name] for p in t.parameters))
    )
    checking.verify_binding(accepted)
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert accepted.arguments == probe.decoded_arguments(document, values)
