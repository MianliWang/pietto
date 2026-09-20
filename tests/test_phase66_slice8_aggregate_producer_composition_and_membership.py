"""Aggregate producer composition, transport and SEMI/ANTI membership.

Every input here is an ordinary authored project built through the installed
production pipeline, and every membership verdict is taken from the emitted bytes
and the independent public consumer. Nothing constructs a plan, a completion entry
or a joined port by hand.
"""

import json
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectExistingEffectiveOutput,
    ProjectNoJoinGroupedOutput,
)
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")


def emit(tmp_path, target, case, variant):
    item = probe.fixture(target, case, variant)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


def document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def public(outcome) -> dict[str, Any]:
    return probe.decode_public(serialize_project_sql_emission(outcome))


def entry(checked, name):
    found = [
        item
        for item in checked.completed.effective_outputs.entries
        if item.owner.definition.name == name
    ]
    assert len(found) == 1
    return found[0]


def origin(data, label):
    correspondence = [item for item in data["columns"] if item["label"] == label][0][
        "correspondence"
    ]
    return correspondence.get("aggregate_origin") or correspondence.get(
        "aggregate_transport"
    )


# --------------------------------------------------------------------------
# The authorized aggregate-producer completion route
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("case", "variant", "mode"),
    (
        ("Z_aggregate_membership", "semi_global", ProjectJoinedAggregationMode.GLOBAL),
        (
            "Z_aggregate_membership",
            "semi_grouped",
            ProjectJoinedAggregationMode.GROUPED,
        ),
        ("Z_aggregate_transport", "outer_null", ProjectJoinedAggregationMode.GROUPED),
    ),
)
def test_an_aggregate_join_producer_uses_the_current_route(
    tmp_path, target, case, variant, mode
):
    """Only a successful, fully verified aggregate result is admitted."""
    checked, outcome = emit(tmp_path, target, case, variant)
    producer = entry(checked, "g" if case == "Z_aggregate_membership" else "grouped")
    assert type(producer) is ProjectCompletedEffectiveOutput
    root = producer.root
    assert type(root) is ProjectConcreteNoJoinReplay
    assert root.mode is mode
    readiness = root.aggregate_readiness
    assert readiness is not None and readiness.status.value == "concrete"
    assert all(
        type(item.source) is ProjectNoJoinGroupedOutput for item in producer.fields
    )
    assert not root.window_outputs
    assert outcome.status == "VERIFIED"


@pytest.mark.parametrize("target", TARGETS)
def test_a_producer_no_join_needs_keeps_its_established_route(tmp_path, target):
    """Promotion is a current-JOIN route choice, never a blanket reclassification."""
    checked, outcome = emit(tmp_path, target, "Z_aggregate_composition", "named")
    # No JOIN consumes this grouped producer, so its historical base route and
    # its own properties are exactly what they were before this Slice.
    assert type(entry(checked, "grouped")) is ProjectExistingEffectiveOutput
    assert type(entry(checked, "agg")) is ProjectExistingEffectiveOutput
    assert outcome.status == "VERIFIED"


# --------------------------------------------------------------------------
# Named, imported and downstream composition
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("named", "imported"))
def test_a_named_or_imported_aggregate_reaches_an_ordinary_consumer(
    tmp_path, target, variant
):
    _, outcome = emit(tmp_path, target, "Z_aggregate_composition", variant)
    data = document(outcome)
    assert outcome.status == "VERIFIED"
    assert data["sql"].count("COUNT(*)") == 1
    # The transported value still declares that it is a grouped result.
    assert origin(data, "b")["role"] == "aggregate_result"
    assert origin(data, "a")["role"] == "group_key"
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_an_ordinary_consumer_filters_an_established_aggregate_output(tmp_path, target):
    _, outcome = emit(tmp_path, target, "Z_aggregate_composition", "downstream_filter")
    sql = document(outcome)["sql"]
    assert sql.index(" GROUP BY ") < sql.rindex(" WHERE ")
    assert sql.count("COUNT(*)") == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_named_global_result_may_be_filtered_by_a_later_query(tmp_path, target):
    """The supported composition that GLOBAL+satisfying source syntax is not."""
    _, outcome = emit(tmp_path, target, "Z_aggregate_membership", "filtered_global")
    sql = document(outcome)["sql"]
    assert outcome.status == "VERIFIED"
    assert "GROUP BY" not in sql
    assert sql.count("COUNT(*)") == 1
    assert " WHERE EXISTS (" in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_pre_group_let_and_filter_stay_their_own_stages(tmp_path, target):
    _, outcome = emit(tmp_path, target, "Z_aggregate_composition", "let_where")
    sql = document(outcome)["sql"]
    assert sql.index(" WHERE ") < sql.index(" GROUP BY ")
    public(outcome)


# --------------------------------------------------------------------------
# JOIN into aggregation, and aggregation out through JOIN
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_aggregation_counts_joined_occurrences(tmp_path, target):
    """A legitimate joined COUNT counts occurrences, never unique base entities."""
    _, outcome = emit(tmp_path, target, "Z_aggregate_joined", "inner_fanout")
    sql = document(outcome)["sql"]
    assert " INNER JOIN " in sql
    assert sql.index(" INNER JOIN ") < sql.index(" GROUP BY ")
    assert "DISTINCT" not in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_an_unmatched_left_occurrence_separates_the_two_counts(tmp_path, target):
    _, outcome = emit(tmp_path, target, "Z_aggregate_joined", "left_nullable")
    data = document(outcome)
    assert " LEFT JOIN " in data["sql"]
    assert data["sql"].count("COUNT(") == 2
    assert origin(data, "total")["arguments"] == []
    assert len(origin(data, "cf")["arguments"]) == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_an_accumulated_right_join_feeds_its_aggregation(tmp_path, target):
    _, outcome = emit(tmp_path, target, "Z_aggregate_joined", "right_accumulated")
    sql = document(outcome)["sql"]
    assert " RIGHT JOIN " in sql and sql.index(" RIGHT JOIN ") < sql.index(" GROUP BY ")
    public(outcome)


def test_a_restricted_full_join_feeds_its_aggregation_on_postgres(tmp_path):
    _, outcome = emit(tmp_path, "postgres", "Z_aggregate_joined", "full_restricted")
    sql = document(outcome)["sql"]
    assert " FULL JOIN " in sql and sql.index(" FULL JOIN ") < sql.index(" GROUP BY ")
    public(outcome)


def test_the_same_full_aggregation_stays_a_typed_mysql_blocker(tmp_path):
    _, outcome = emit(tmp_path, "mysql", "Z_aggregate_joined", "full_restricted")
    assert outcome.status == "BLOCKED"
    assert any(
        item.detail == "mysql_full_join_approved_non_support"
        for item in outcome.blockers
    )
    # The neighbouring joined aggregations still emit on the same target.
    for variant in ("inner_fanout", "left_nullable", "right_accumulated"):
        _, other = emit(tmp_path / variant, "mysql", "Z_aggregate_joined", variant)
        assert other.status == "VERIFIED"


@pytest.mark.parametrize("target", TARGETS)
def test_an_unmatched_grouped_count_is_nulled_and_never_rebuilt(tmp_path, target):
    """C07/R08 over an aggregate value: outer nulling, not a recomputed zero."""
    _, outcome = emit(tmp_path, target, "Z_aggregate_transport", "outer_null")
    data = document(outcome)
    sql = data["sql"]
    assert " LEFT JOIN " in sql
    # The count is computed once, below the JOIN, and only carried afterwards.
    assert sql.count("COUNT(*)") == 1
    assert sql.index("COUNT(*)") < sql.index(" LEFT JOIN ")
    assert "COALESCE" not in sql.upper()
    transported = [item for item in data["columns"] if item["label"] == "b"][0]
    assert transported["nullable"] is True
    # The nulled port keeps the count's own non-negative signed64 domain.
    assert transported["representation"]["domain"]["min"] == "0"
    assert origin(data, "b")["role"] == "aggregate_result"
    public(outcome)


# --------------------------------------------------------------------------
# R11/C09: the GROUPED and GLOBAL right terminals
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("variant", "wrapper"),
    (
        ("semi_global", " WHERE EXISTS ("),
        ("anti_global", " WHERE NOT EXISTS ("),
        ("semi_grouped", " WHERE EXISTS ("),
        ("anti_grouped", " WHERE NOT EXISTS ("),
        ("satisfying_right", " WHERE EXISTS ("),
    ),
)
def test_membership_wraps_the_complete_aggregate_right_terminal(
    tmp_path, target, variant, wrapper
):
    _, outcome = emit(tmp_path, target, "Z_aggregate_membership", variant)
    sql = document(outcome)["sql"]
    assert wrapper in sql
    assert " NOT IN " not in sql and " IN (" not in sql
    # The right producer keeps its own aggregation instead of a base-table scan.
    assert sql.count("COUNT(*)") == 1
    assert sql.index("COUNT(*)") < sql.index(wrapper)
    # The generated sentinel is a structural constant, never an authored slot.
    assert "SELECT 1 FROM" in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("variant", "grouped"),
    (("semi_global", False), ("semi_grouped", True), ("satisfying_right", True)),
)
def test_a_membership_right_keeps_its_grouping_and_its_satisfying(
    tmp_path, target, variant, grouped
):
    _, outcome = emit(tmp_path, target, "Z_aggregate_membership", variant)
    sql = document(outcome)["sql"]
    assert (" GROUP BY " in sql) is grouped
    if variant == "satisfying_right":
        # The retained groups come from a post-aggregation predicate stage.
        assert sql.index(" GROUP BY ") < sql.rindex(" WHERE ")
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_membership_left_schema_never_gains_a_right_output(tmp_path, target):
    for variant in ("semi_global", "anti_grouped", "satisfying_right"):
        _, outcome = emit(tmp_path / variant, target, "Z_aggregate_membership", variant)
        data = document(outcome)
        assert [item["label"] for item in data["columns"]] == ["a"]
        assert data["columns"][0]["correspondence"].get("aggregate_origin") is None
        assert data["columns"][0]["correspondence"].get("aggregate_transport") is None


def test_dropping_a_membership_aggregation_is_rejected(tmp_path):
    """A coordinated removal of the right aggregation must not decode."""
    _, outcome = emit(tmp_path, "postgres", "Z_aggregate_membership", "semi_grouped")
    data = document(outcome)
    sql = data["sql"]
    data["sql"] = sql.replace(' GROUP BY "s0"."group key"', "", 1)
    data["requirements"] = [
        item
        for item in data["requirements"]
        if item["kind"] not in {"aggregation", "group_key"}
    ]
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_replacing_a_membership_producer_with_a_base_scan_is_rejected(tmp_path):
    _, outcome = emit(tmp_path, "postgres", "Z_aggregate_membership", "semi_global")
    data = document(outcome)
    sql = data["sql"]
    data["sql"] = sql.replace("COUNT(*)", '"s0"."group key"', 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


# --------------------------------------------------------------------------
# Preserved upstream boundaries
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_field_aggregate_without_grain_evidence_stays_unavailable(
    tmp_path, target
):
    """Transportability grants no grain proof; the risk requirement still binds."""
    header = probe.AGGREGATE_HEADER.format(target=target)
    item = probe.aggregate_fixture(target, "Z_aggregate_joined", "inner_fanout")
    body = """query result:
    from agg
    inner join agg as r:
        from agg
        on agg.key == r.key
    group by:
        agg.key
    select:
        k = agg.key
        cf = count(r.value)
"""
    _, outcome = probe.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_computed_group_key_is_still_not_an_admitted_source_shape(tmp_path, target):
    header = probe.AGGREGATE_HEADER.format(target=target)
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    body = """query result:
    from agg
    let:
        shifted = key + 1
    group by:
        shifted
    select:
        total = count()
"""
    _, outcome = probe.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


@pytest.mark.parametrize("target", TARGETS)
def test_pure_grouping_without_an_aggregate_is_still_unavailable(tmp_path, target):
    header = probe.AGGREGATE_HEADER.format(target=target)
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    body = """query result:
    from agg
    group by:
        key
    select:
        k = key
"""
    _, outcome = probe.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


# --------------------------------------------------------------------------
# The published manifest agrees with the installed pipeline
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_every_aggregate_manifest_variant_reaches_its_declared_outcome(
    tmp_path, target
):
    for case in probe.AGGREGATE_CASES:
        for variant in probe.VARIANTS[case]:
            expected = probe.expected_status(case, variant, target)
            _, outcome = emit(tmp_path / f"{case}-{variant}", target, case, variant)
            assert outcome.status == expected, (case, variant, outcome.status)
            if expected == "VERIFIED":
                assert public(outcome)["status"] == "VERIFIED"
