"""The current-route promotion that makes JOIN input values transportable.

Every input here is an ordinary authored project built through the installed
production pipeline. Nothing in this file constructs a plan, a completion entry or
a joined port by hand, and no expectation is read back out of the artifact it is
meant to check.
"""

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
    ProjectNoJoinGroupedOutput,
)
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto._project.project_ir_properties import ProjectIRJoinedRowField
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_joins import ProjectSQLJoinPortKind

TARGETS = ("postgres", "mysql")

# One JOIN input producer per admitted body shape. `marker` is an authored
# literal, `computed` an ordinary arithmetic value and `doubled` the result of an
# ordered LET chain: before this Slice each one made the whole producer row
# lineage non-concrete, so the joined tail never reached emission at all.
PRODUCERS = {
    "literal": "table prod:\n    from rhs\n    select:\n        pid = id\n        marker = 1\n",
    "computed": "table prod:\n    from rhs\n    select:\n        pid = id\n        computed = id + id\n",
    "let": (
        "table prod:\n    from rhs\n    let:\n        step = id + 1\n"
        "        twice = step + step\n    select:\n        pid = id\n        doubled = twice\n"
    ),
    # Controls: a pure field projection and a filter-only body were always
    # concrete, and must keep their established historical route.
    "field_only": "table prod:\n    from rhs\n    select:\n        pid = id\n",
    "where_only": "table prod:\n    from rhs\n    where id > 0\n    select:\n        pid = id\n",
}
PROMOTED = ("literal", "computed", "let")
UNCHANGED = ("field_only", "where_only")
# A later-owner stage keeps the historical route even though its select list looks
# scalar. Slice8 implements the aggregate branch, so only the window body is still
# excluded here; both sources are authored in the real accepted surface, because a
# body that never parses would prove nothing about the promotion at all.
# Slice9 implemented the window branch of this exclusion, so the retained
# negative is now a window producer that still carries a later relation barrier.
# Its ORDER belongs to Slice10, so the body keeps its established base route.
EXCLUDED = {
    "window_order": (
        "table prod:\n    from rhs\n    select:\n        pid = id\n"
        "        at = row_number() window:\n            order by:\n                id\n"
        "    order by:\n        pid\n"
    ),
}
# Slice9's authorized window-producer completion route: this body now reaches
# the current route with its own completed window results.
WINDOW_PRODUCER = (
    "table prod:\n    from rhs\n    select:\n        pid = id\n"
    "        at = row_number() window:\n            order by:\n                id\n"
)
# Slice8's authorized aggregate-producer completion route: this body now reaches
# the current route with its own grouped readiness instead of the base route.
AGGREGATE_PRODUCER = (
    "table prod:\n    from rhs\n    group by:\n        id\n"
    "    select:\n        pid = id\n        total = count()\n"
)

CONSUMER = """query result:
    from lhs
    {kind} join prod as r:
        from lhs
        on lhs.id == r.pid
    select:
        a = lhs.id
        b = r.pid
"""


def build(tmp_path, target, source, *, link=False, policy="preserve_literals"):
    item = probe.join_witness(target, source, link=link, policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


def _completed(tmp_path, target, source):
    """Parse and complete one authored project without reaching emission."""
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
        ProjectConcreteCompletedSemanticResult,
    )

    item = probe.join_witness(target, source)
    directory = tmp_path / "completion"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(probe.CONFIG)
    (directory / "main.pietto").write_text(item["source"], encoding="utf-8")
    parsed = check_project_parse_only(directory)
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert type(completed) is ProjectConcreteCompletedSemanticResult
    return parsed.ok, completed


def _entry(completed, name):
    found = [
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == name
    ]
    assert len(found) == 1
    return found[0]


def producer_entry(checked, name="prod"):
    """The completed-output entry the installed completion chose for one owner."""
    completion = checked.completed.effective_outputs
    found = [
        entry for entry in completion.entries if entry.owner.definition.name == name
    ]
    assert len(found) == 1
    return found[0]


def verified_plan(checked):
    """The plan this candidate actually produced, not an unavailable placeholder."""
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    return plan


def joined_field(port):
    """One published JOIN port's joined-row field, with its own exact identity."""
    field = port.field
    assert type(field) is ProjectIRJoinedRowField
    return field


def output_ports(plan, join):
    return [
        port
        for port in plan.join_ports
        if port.block is join.ref and port.kind is ProjectSQLJoinPortKind.OUTPUT
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", PROMOTED)
def test_a_scalar_producer_body_reaches_the_current_join_route(tmp_path, target, shape):
    """A literal, a computed value and an ordered LET all become transportable."""
    checked, outcome = build(
        tmp_path, target, PRODUCERS[shape] + CONSUMER.format(kind="left")
    )
    assert type(producer_entry(checked)) is ProjectCompletedEffectiveOutput
    assert outcome.status == "VERIFIED", [
        (item.code, item.detail) for item in outcome.blockers
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", UNCHANGED)
def test_an_already_concrete_producer_keeps_its_established_route(
    tmp_path, target, shape
):
    """Promotion is not applied where the historical route already succeeded."""
    checked, outcome = build(
        tmp_path, target, PRODUCERS[shape] + CONSUMER.format(kind="left")
    )
    assert type(producer_entry(checked)) is ProjectExistingEffectiveOutput
    assert outcome.status == "VERIFIED"


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(EXCLUDED))
def test_a_later_owner_body_is_excluded_from_the_promotion(tmp_path, target, shape):
    """A later-barrier body keeps its established route and its own diagnostic.

    The source parses and completes: the producer stays on the base route and the
    joined tail stays non-concrete with PIE-S2333, so this is a real retained
    negative rather than an input the harness never accepted.
    """
    source = EXCLUDED[shape] + CONSUMER.format(kind="left")
    parsed, completed = _completed(tmp_path, target, source)
    assert parsed is True
    entry = _entry(completed, "prod")
    assert type(entry) is ProjectExistingEffectiveOutput
    result = _entry(completed, "result")
    assert type(result) is ProjectEffectiveOutputCompletionTerminal
    assert result.reason.value == "current_join_tail_non_concrete"
    assert [item.code for item in completed.diagnostics] == ["PIE-S2333"]
    # Emission still receives no usable plan for this input, exactly as before.
    _, outcome = build(tmp_path / shape, target, source)
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_producer_now_reaches_the_current_join_route(tmp_path, target):
    """Slice9 migrates the window branch of that exclusion to real behavior.

    The producer's own completed window result is what the JOIN transports, so
    the consumer reads the established stage output rather than the historical
    source-root projection. Transportability still grants no relationship
    endpoint and no M1/M2/M4 guarantee.
    """
    checked, outcome = build(
        tmp_path, target, WINDOW_PRODUCER + CONSUMER.format(kind="left")
    )
    entry = producer_entry(checked)
    assert type(entry) is ProjectCompletedEffectiveOutput
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert "ROW_NUMBER()" in artifact.rendered.sql.decode()


@pytest.mark.parametrize("target", TARGETS)
def test_an_aggregate_producer_now_reaches_the_current_join_route(tmp_path, target):
    """Slice8 migrates the aggregate branch of that exclusion to real behavior."""
    checked, outcome = build(
        tmp_path, target, AGGREGATE_PRODUCER + CONSUMER.format(kind="left")
    )
    entry = producer_entry(checked)
    assert type(entry) is ProjectCompletedEffectiveOutput
    root = entry.root
    assert type(root) is ProjectConcreteNoJoinReplay
    assert root.mode is ProjectJoinedAggregationMode.GROUPED
    readiness = root.aggregate_readiness
    assert readiness is not None and readiness.status.value == "concrete"
    # The promoted value is the grouped result, never the raw source row.
    assert all(type(item.source) is ProjectNoJoinGroupedOutput for item in entry.fields)
    assert outcome.status == "VERIFIED", [
        (item.code, item.detail) for item in outcome.blockers
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_an_ordered_or_limited_aggregate_producer_keeps_its_base_route(
    tmp_path, target
):
    """A result barrier is not smuggled through the aggregate promotion."""
    source = AGGREGATE_PRODUCER.replace(
        "        total = count()\n",
        "        total = count()\n    order by:\n        pid\n    limit 2\n",
    )
    _, completed = _completed(tmp_path, target, source + CONSUMER.format(kind="left"))
    assert type(_entry(completed, "prod")) is ProjectExistingEffectiveOutput


@pytest.mark.parametrize("target", TARGETS)
def test_a_promoted_right_side_value_is_null_extended_exactly_once(tmp_path, target):
    """C07: an unmatched LEFT row nulls the literal it carries, with one cause."""
    checked, outcome = build(
        tmp_path,
        target,
        PRODUCERS["literal"]
        + """query result:
    from lhs
    left join prod as r:
        from lhs
        on lhs.id == r.pid
    select:
        a = lhs.id
        b = r.pid
        m = r.marker
""",
    )
    assert outcome.status == "VERIFIED"
    plan = verified_plan(checked)
    (join,) = plan.joins
    ports = output_ports(plan, join)
    left_width = len(
        [item for item in plan.join_inputs if item.ref is join.inputs[0]][0].ports
    )
    # The preserved left side keeps its OWN declared domain and gains no cause:
    # `id` stays non-null and the declared-nullable `key` stays nullable without
    # a JOIN ever being blamed for it.
    left = ports[:left_width]
    assert [joined_field(item).nulling_joins for item in left] == [()] * left_width
    assert [joined_field(item).effective_nullability for item in left] == [
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NULLABLE,
    ]
    # The null-extended right side carries exactly one cause per port, including
    # the port whose value is an authored literal rather than a source column.
    right = ports[left_width:]
    assert right and all(len(joined_field(item).nulling_joins) == 1 for item in right)
    assert all(
        joined_field(item).effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in right
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("kind", "nulled_sides"),
    (
        ("cross", ()),
        ("inner", ()),
        ("left", (1,)),
        ("right", (0,)),
    ),
)
def test_each_join_kind_null_extends_exactly_its_own_side(
    tmp_path, target, kind, nulled_sides
):
    """Ordered nulling causes, derived from the kind rather than from the value."""
    condition = "" if kind == "cross" else "        on lhs.id == r.id\n"
    checked, outcome = build(
        tmp_path,
        target,
        f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
{condition}    select:
        a = lhs.id
""",
    )
    assert outcome.status == "VERIFIED"
    plan = verified_plan(checked)
    (join,) = plan.joins
    inputs = {item.ref: item for item in plan.join_inputs}
    widths = [len(inputs[reference].ports) for reference in join.inputs]
    for position, port in enumerate(output_ports(plan, join)):
        side = 0 if position < widths[0] else 1
        assert len(joined_field(port).nulling_joins) == (
            1 if side in nulled_sides else 0
        )


@pytest.mark.parametrize("target", TARGETS)
def test_an_accumulated_right_join_nulls_the_whole_retained_left(tmp_path, target):
    """R08/C08: RIGHT null-extends every earlier port, not only the newest one."""
    checked, outcome = build(
        tmp_path,
        target,
        """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    right join rhs as s:
        from lhs
        on lhs.id == s.id
    select:
        a = lhs.id
""",
    )
    assert outcome.status == "VERIFIED"
    plan = verified_plan(checked)
    first, second = sorted(plan.joins, key=lambda join: join.position)
    inputs = {item.ref: item for item in plan.join_inputs}
    accumulated = len(inputs[second.inputs[0]].ports)
    ports = output_ports(plan, second)
    assert [len(joined_field(port).nulling_joins) for port in ports[:accumulated]] == [
        1
    ] * (accumulated)
    assert [len(joined_field(port).nulling_joins) for port in ports[accumulated:]] == [
        0
    ] * (len(ports) - accumulated)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_a_membership_join_publishes_only_its_left_side(tmp_path, target, kind):
    checked, outcome = build(
        tmp_path,
        target,
        f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
""",
    )
    assert outcome.status == "VERIFIED"
    plan = verified_plan(checked)
    (join,) = plan.joins
    inputs = {item.ref: item for item in plan.join_inputs}
    assert len(join.outputs) == len(inputs[join.inputs[0]].ports)
    assert all(
        not joined_field(port).nulling_joins for port in output_ports(plan, join)
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left"))
def test_a_relationship_via_route_keeps_its_retained_equality(tmp_path, target, kind):
    """The optional current route never invents or drops a relationship equality."""
    checked, outcome = build(
        tmp_path,
        target,
        f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
        via link: l -> r
    select:
        a = lhs.id
""",
        link=True,
    )
    assert outcome.status == "VERIFIED"
    (join,) = verified_plan(checked).joins
    assert len(join.equalities) == 1 and join.on is None


@pytest.mark.parametrize("target", TARGETS)
def test_a_via_route_refined_by_an_authored_predicate_keeps_both(tmp_path, target):
    checked, outcome = build(
        tmp_path,
        target,
        """query result:
    from lhs
    inner join rhs as r:
        from lhs
        via link: l -> r
        on lhs.key == r.key
    select:
        a = lhs.id
""",
        link=True,
    )
    assert outcome.status == "VERIFIED"
    (join,) = verified_plan(checked).joins
    assert len(join.equalities) == 1 and join.on is not None


@pytest.mark.parametrize("target", TARGETS)
def test_a_promoted_endpoint_keeps_the_relationship_guarantee_unavailable(
    tmp_path, target
):
    """A precise upstream negative, retained rather than worked around.

    Becoming transportable does not make a value a relationship endpoint: the
    M1/M2/M4 guarantee still needs historical properties this producer has none
    of. This input failed before the promotion too, and it must keep failing --
    it is not a successful promoted-`via` witness and discharges no obligation.
    """
    checked, outcome = build(
        tmp_path,
        target,
        """relationship prodlink:
    endpoint l: lhs
    endpoint p: prod
    on l.id == p.pid
"""
        + PRODUCERS["literal"]
        + """query result:
    from lhs
    inner join prod as r:
        from lhs
        via prodlink: l -> p
    select:
        a = lhs.id
""",
    )
    # The producer itself IS promoted; only the relationship guarantee over it
    # stays unavailable, and the established base route keeps its own reason.
    assert type(producer_entry(checked)) is ProjectCompletedEffectiveOutput
    entry = producer_entry(checked, "result")
    assert type(entry) is ProjectEffectiveOutputTerminal
    assert entry.reason.value == "joined_completion_non_concrete"
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_two_level_producer_chain_is_promoted_transitively(tmp_path, target):
    """The blocked lineage was transitive, so the repair must be too."""
    checked, outcome = build(
        tmp_path,
        target,
        """table base:
    from rhs
    select:
        bid = id
        marker = 1
table prod:
    from base
    select:
        pid = bid
        kept = marker
"""
        + CONSUMER.format(kind="left"),
    )
    assert outcome.status == "VERIFIED"
    assert type(producer_entry(checked, "base")) is ProjectCompletedEffectiveOutput
