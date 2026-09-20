"""GROUPED/GLOBAL aggregation, satisfying and aggregate result representations.

Every artifact below is produced by the installed emission path from an ordinary
authored project, and every verdict is taken from the independent public consumer
reading the published bytes. No production builder, realization function or
renderer is called to decide whether a public document is acceptable.
"""

import json
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")
SIGNED64 = "9223372036854775807"


def emit(tmp_path, target, case, variant):
    """One published aggregation fixture through the installed pipeline."""
    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return outcome


def emit_source(tmp_path, target, body, *, policy="preserve_literals"):
    """One ad-hoc aggregation body over the fixed aggregation source shape."""
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    contract = json.loads(item["contract"])
    if policy == "bind_safe_literals":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = probe.AGGREGATE_HEADER.format(target=target)
    _, outcome = probe.build_case(
        tmp_path, header + body, probe.encoded(contract).decode(), policy
    )
    return outcome


def document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def public(outcome) -> dict[str, Any]:
    """The independent consumer's verdict over the published bytes alone."""
    return probe.decode_public(serialize_project_sql_emission(outcome))


def column(data, label):
    found = [item for item in data["columns"] if item["label"] == label]
    assert len(found) == 1
    return found[0]


def origin(data, label):
    correspondence = column(data, label)["correspondence"]
    return (
        correspondence.get("aggregate_origin") or correspondence["aggregate_transport"]
    )


# --------------------------------------------------------------------------
# Native grouping structure
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_global_aggregation_emits_no_grouping_at_all(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    assert "GROUP BY" not in data["sql"]
    assert data["sql"].count("COUNT(*)") == 1
    public(emit(tmp_path, target, "X_aggregate_global", "bag"))


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_aggregation_binds_group_by_to_its_input_column(tmp_path, target):
    """GROUP BY names the actual pre-aggregate value, never an alias or ordinal."""
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "hidden")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    binding = f" GROUP BY {quote}s0{quote}.{quote}group key{quote}"
    assert binding in sql
    assert " GROUP BY 1" not in sql and " GROUP BY 2" not in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_constant_valued_determinant_groups_by_its_established_value(
    tmp_path, target
):
    """C10: the constant key is a producer port, not the ordinal position one."""
    outcome = emit(tmp_path, target, "Y_aggregate_constant", "grouped")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    assert f" GROUP BY {quote}s1{quote}.{quote}c1{quote}" in sql
    assert " GROUP BY 1" not in sql
    # The producer materializes the constant once; grouping reads that port.
    assert "CAST(1 AS " in sql and sql.index("CAST(1 AS ") < sql.index(" GROUP BY ")
    # The selected label is spelled exactly like a generated column name and
    # still captures nothing: the final SELECT names its own stage column.
    assert f"{quote}t2{quote}.{quote}c0{quote} AS {quote}c0{quote}" in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_hidden_determinant_stays_out_of_the_visible_result(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "hidden")
    data = document(outcome)
    assert [item["label"] for item in data["columns"]] == ["total", "cf"]
    # The determinant is still a real grouping column inside the stage.
    assert " GROUP BY " in data["sql"]
    assert all(
        item["correspondence"]["aggregate_origin"]["role"] == "aggregate_result"
        for item in data["columns"]
    )
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_multiple_determinants_keep_their_order_rename_and_repeat(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "visible")
    data = document(outcome)
    assert [item["label"] for item in data["columns"]] == [
        "f",
        "renamed",
        "again",
        "total",
    ]
    # Two visible outputs project the same determinant; each keeps its own
    # projection while naming the one retained group key.
    first, second = origin(data, "renamed"), origin(data, "again")
    assert first["determinant"] == second["determinant"]
    assert (
        column(data, "renamed")["correspondence"]["projection"]
        != column(data, "again")["correspondence"]["projection"]
    )
    assert origin(data, "f")["determinant"] != first["determinant"]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_two_identical_declarations_keep_two_result_ports(tmp_path, target):
    """No CSE: repeated aggregates are distinct occurrences with distinct ports."""
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        a = count()
        b = count()
""",
    )
    data = document(outcome)
    assert data["sql"].count("COUNT(*)") == 2
    left, right = origin(data, "a"), origin(data, "b")
    assert left["aggregate"] != right["aggregate"]
    assert left["result"] != right["result"]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_no_representative_row_repair_is_emitted(tmp_path, target):
    """ONLY_FULL_GROUP_BY stays on: no ANY_VALUE and no wrapping repair."""
    for variant in ("hidden", "visible"):
        sql = document(emit(tmp_path, target, "X_aggregate_grouped", variant))["sql"]
        assert "ANY_VALUE" not in sql and "any_value" not in sql
        assert "DISTINCT" not in sql
        assert "sql_mode" not in sql.lower()


# --------------------------------------------------------------------------
# Function identity and result domains
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_each_promised_function_keeps_its_own_spelling(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_global", "bag")
    data = document(outcome)
    sql = data["sql"]
    quote = '"' if target == "postgres" else "`"
    value = f"{quote}s0{quote}.{quote}value é{quote}"
    assert "COUNT(*)" in sql
    assert f"COUNT({value})" in sql
    assert f"COUNT(DISTINCT {value})" in sql
    assert f"MIN({value})" in sql and f"MAX({value})" in sql
    assert [
        origin(data, label)["function"] for label in ("c", "cf", "cd", "lo", "hi")
    ] == [
        "count",
        "count",
        "count_distinct",
        "min",
        "max",
    ]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_row_count_declares_the_whole_input_and_no_argument(tmp_path, target):
    """Count's empty scalar argument set is not an empty dependency set."""
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    row_count, field_count = origin(data, "c"), origin(data, "cf")
    assert row_count["arguments"] == []
    assert len(row_count["inputs"]) == 7
    assert len(field_count["arguments"]) == 1 and len(field_count["inputs"]) == 1
    assert field_count["inputs"] != row_count["inputs"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_count_result_is_non_null_and_not_its_argument_range(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    for label in ("c", "cf", "cd"):
        published = column(data, label)
        assert published["nullable"] is False
        assert published["representation"]["domain"] == {
            "kind": "int_range",
            "min": "0",
            "max": SIGNED64,
        }
        assert published["representation"]["storage"] == {
            "kind": "pg_int8" if target == "postgres" else "my_bigint"
        }


@pytest.mark.parametrize("target", TARGETS)
def test_an_extreme_value_admits_null_over_a_non_null_argument(tmp_path, target):
    """An empty or all-null input has no extreme value, so the result is nullable."""
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        lo = min(rid)
        hi = max(rid)
""",
    )
    data = document(outcome)
    source_field = [item for item in data["columns"] if item["label"] == "lo"][0][
        "representation"
    ]
    assert source_field["nullable"] is True
    assert source_field["domain"] == {
        "kind": "int_range",
        "min": "-9007199254740993",
        "max": "9007199254740993",
    }
    assert column(data, "hi")["nullable"] is True
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_count_result_does_not_license_wider_arithmetic(tmp_path, target):
    """A nonnegative signed64 count cannot be incremented without overflow room."""
    outcome = emit_source(
        tmp_path,
        target,
        """table grouped:
    from agg
    select:
        total = count()
query result:
    from grouped
    select:
        bumped = total + total
""",
    )
    assert outcome.status == "BLOCKED"
    assert any(
        item.code == "PIE-B1002" and item.detail == "arithmetic_outside_physical_range"
        for item in outcome.blockers
    )


# --------------------------------------------------------------------------
# Empty input and NULL behavior
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("variant", "mode", "empty_input"),
    (
        ("bag", "global", "one_global_row"),
        ("empty", "global", "one_global_row"),
        ("all_null", "global", "one_global_row"),
        ("where_false", "global", "one_global_row"),
    ),
)
def test_a_global_result_declares_its_one_row_disposition(
    tmp_path, target, variant, mode, empty_input
):
    data = document(emit(tmp_path, target, "X_aggregate_global", variant))
    for label in ("c", "cf", "cd", "lo", "hi"):
        item = origin(data, label)
        assert (item["mode"], item["empty_input"]) == (mode, empty_input)


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_result_declares_zero_groups_on_empty_input(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_grouped", "empty"))
    assert origin(data, "total")["empty_input"] == "no_groups"
    assert origin(data, "total")["mode"] == "grouped"


@pytest.mark.parametrize("target", TARGETS)
def test_a_false_pre_input_filter_keeps_the_global_row_stage(tmp_path, target):
    """WHERE false is its own stage below the aggregation, never a folded result."""
    outcome = emit(tmp_path, target, "X_aggregate_global", "where_false")
    sql = document(outcome)["sql"]
    assert " WHERE " in sql and sql.index(" WHERE ") < sql.rindex("COUNT(*)")
    public(outcome)


# --------------------------------------------------------------------------
# satisfying
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_satisfying_is_one_post_aggregation_predicate_over_result_columns(
    tmp_path, target
):
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "retained")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    # The aggregation publishes its own stage; the predicate reads that stage's
    # result columns in a later SELECT, never the pre-aggregate input.
    grouping = sql.index(" GROUP BY ")
    predicate = sql.rindex(" WHERE ")
    assert grouping < predicate
    # The predicate reads the aggregation stage's own result columns.
    assert f"{quote}t1{quote}.{quote}c1{quote} <" in sql
    assert f"{quote}t1{quote}.{quote}c2{quote} >" in sql
    assert "HAVING" not in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_satisfying_use_is_a_use_and_not_a_new_computation(tmp_path, target):
    """Three authored references resolve to one already-established result."""
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "retained")
    sql = document(outcome)["sql"]
    assert sql.count("COUNT(*)") == 1 and sql.count("MIN(") == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_unique_aggregate_let_reference_reuses_its_result_port(tmp_path, target):
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "let_reference")
    sql = document(outcome)["sql"]
    assert sql.count("COUNT(") == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_satisfying_literal_stays_specialized_under_bind_safe(tmp_path, target):
    """The extraction rule never admits a satisfying slot; a WHERE literal binds."""
    bound = document(emit(tmp_path, target, "Y_aggregate_satisfying", "bind"))
    assert bound["request"]["literal_policy"] == "bind_safe_literals"
    assert bound["parameter_uses"] == [] and bound["fixed_values"] == []
    preserved = document(emit(tmp_path, target, "Y_aggregate_satisfying", "retained"))
    assert preserved["sql"] == bound["sql"]
    public(emit(tmp_path, target, "Y_aggregate_satisfying", "bind"))


@pytest.mark.parametrize("target", TARGETS)
def test_a_pre_group_filter_literal_still_binds(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    where key > 0
    group by:
        key
    select:
        total = count()
""",
        policy="bind_safe_literals",
    )
    data = document(outcome)
    assert len(data["fixed_values"]) == 1 and len(data["parameter_uses"]) == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_filtering_before_and_after_aggregation_are_different_stages(tmp_path, target):
    before = document(emit(tmp_path, target, "Y_aggregate_satisfying", "before_input"))
    after = document(emit(tmp_path, target, "Y_aggregate_satisfying", "retained"))
    assert before["sql"].index(" WHERE ") < before["sql"].index(" GROUP BY ")
    assert after["sql"].index(" GROUP BY ") < after["sql"].rindex(" WHERE ")


@pytest.mark.parametrize("target", TARGETS)
def test_global_with_satisfying_stays_rejected_at_its_own_boundary(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        total = count()
    satisfying:
        total > 1
""",
    )
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2333"]


# --------------------------------------------------------------------------
# The exact first-version non-support set
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("sum_direct", "avg_direct", "sum_hidden_right"))
def test_sum_and_avg_keep_their_exact_typed_blocker(tmp_path, target, variant):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    assert outcome.status == "BLOCKED"
    assert [(item.code, item.detail) for item in outcome.blockers] == [
        ("PIE-B1003", "sum_avg_result_realization_rule_not_reviewed_in_phase66")
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_float_determinant_stays_outside_group_comparison(tmp_path, target):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", "float_key")
    assert outcome.status == "BLOCKED"
    assert any(
        item.detail == "group_key_type_outside_reviewed_comparison_domain"
        for item in outcome.blockers
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("bool_domain_key", "decimal_parameter_key"))
def test_a_violated_determinant_domain_is_a_representation_failure(
    tmp_path, target, variant
):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    assert outcome.status == "BLOCKED"
    assert all(item.code == "PIE-B1002" for item in outcome.blockers)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("bool_key", "text_key", "decimal_key"))
def test_the_reviewed_determinant_domains_still_emit(tmp_path, target, variant):
    """The negatives above are domain failures, not a refusal of every key type."""
    outcome = emit(tmp_path, target, "Y_aggregate_domains", variant)
    assert outcome.status == "VERIFIED"
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_an_aggregate_argument_must_be_one_direct_established_field(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        total = count_distinct(label)
""",
    )
    assert outcome.status == "BLOCKED"
    assert any(
        item.detail == "count_distinct_argument_outside_reviewed_int_domain"
        for item in outcome.blockers
    )


# --------------------------------------------------------------------------
# Independent public consumer: finite mutations
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    (
        "count_form",
        "distinct_modifier",
        "grouping_column",
        "grouping_ordinal",
        "extra_grouping_key",
        "dropped_grouping",
        "satisfying_operator",
    ),
)
def test_public_aggregate_byte_corruptions_are_rejected(tmp_path, mutation):
    case, variant = (
        ("Y_aggregate_satisfying", "retained")
        if mutation == "satisfying_operator"
        else ("X_aggregate_global", "bag")
        if mutation in {"count_form", "distinct_modifier"}
        else ("X_aggregate_grouped", "hidden")
    )
    data = document(emit(tmp_path, "postgres", case, variant))
    sql = data["sql"]
    if mutation == "count_form":
        data["sql"] = sql.replace('COUNT("s0"."value é")', "COUNT(*)", 1)
    elif mutation == "distinct_modifier":
        data["sql"] = sql.replace('COUNT(DISTINCT "s0"."value é")', "COUNT(*)", 1)
    elif mutation == "grouping_column":
        data["sql"] = sql.replace(
            ' GROUP BY "s0"."group key"', ' GROUP BY "s0"."value é"', 1
        )
    elif mutation == "grouping_ordinal":
        data["sql"] = sql.replace(' GROUP BY "s0"."group key"', " GROUP BY 1", 1)
    elif mutation == "extra_grouping_key":
        data["sql"] = sql.replace(
            ' GROUP BY "s0"."group key"',
            ' GROUP BY "s0"."group key", "s0"."value é"',
            1,
        )
    elif mutation == "dropped_grouping":
        data["sql"] = sql.replace(' GROUP BY "s0"."group key"', "", 1)
    else:
        data["sql"] = sql.replace(" < ", " > ", 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize(
    "mutation",
    (
        "mode",
        "empty_input",
        "function",
        "determinant",
        "result_port",
        "input_port",
        "arguments",
    ),
)
def test_public_aggregate_provenance_corruptions_are_rejected(tmp_path, mutation):
    data = document(emit(tmp_path, "postgres", "X_aggregate_global", "bag"))
    target = column(data, "cf")["correspondence"]["aggregate_origin"]
    other = column(data, "cd")["correspondence"]["aggregate_origin"]
    if mutation == "mode":
        target["mode"] = "grouped"
    elif mutation == "empty_input":
        target["empty_input"] = "no_groups"
    elif mutation == "function":
        target["function"] = "count_distinct"
    elif mutation == "determinant":
        target["determinant"] = {"kind": "group_key", "position": 0}
    elif mutation == "result_port":
        target["result"] = other["result"]
    elif mutation == "input_port":
        target["inputs"] = column(data, "c")["correspondence"]["aggregate_origin"][
            "inputs"
        ]
    else:
        target["arguments"] = []
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize(
    "kinds",
    (
        ("aggregation",),
        ("group_key",),
        ("aggregate",),
        ("result_projection",),
        ("satisfying_root",),
    ),
)
def test_deleting_an_aggregate_requirement_family_is_rejected(tmp_path, kinds):
    case, variant = (
        ("Y_aggregate_satisfying", "retained")
        if "satisfying_root" in kinds
        else ("X_aggregate_grouped", "hidden")
    )
    data = document(emit(tmp_path, "postgres", case, variant))
    before = len(data["requirements"])
    data["requirements"] = [
        item for item in data["requirements"] if item["kind"] not in kinds
    ]
    assert len(data["requirements"]) < before
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_a_coordinated_stage_and_requirement_deletion_is_rejected(tmp_path):
    """Removing a determinant everywhere must still fail the input denominator."""
    data = document(emit(tmp_path, "postgres", "X_aggregate_grouped", "hidden"))
    sql = data["sql"]
    data["sql"] = sql.replace(' GROUP BY "s0"."group key"', "", 1).replace(
        '"s0"."group key" AS "c0", ', "", 1
    )
    data["requirements"] = [
        item for item in data["requirements"] if item["kind"] != "group_key"
    ]
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("case", "variant"),
    (
        ("X_aggregate_global", "bag"),
        ("X_aggregate_global", "empty"),
        ("X_aggregate_grouped", "hidden"),
        ("X_aggregate_grouped", "visible"),
        ("Y_aggregate_constant", "grouped"),
        ("Y_aggregate_satisfying", "retained"),
        ("Y_aggregate_domains", "text_key"),
    ),
)
def test_valid_aggregate_documents_are_still_accepted(tmp_path, target, case, variant):
    """The controls above must not have turned into a refusal of every document."""
    assert public(emit(tmp_path, target, case, variant))["status"] == "VERIFIED"


# --------------------------------------------------------------------------
# Bounded failure reporting
# --------------------------------------------------------------------------


REPR_LIMIT = 1024


def test_an_aggregate_outcome_repr_stays_bounded(tmp_path):
    """A failing aggregate assertion must not allocate the whole shared graph."""
    item = probe.fixture("postgres", "X_aggregate_grouped", "visible")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    for text in (repr(outcome), repr(artifact)):
        assert len(text) < REPR_LIMIT
    # The realized aggregation stage is graph bearing; its own display must stay
    # a bounded summary rather than an expansion of every retained product.
    query = artifact.ast
    assert type(query) is SQLRowQuery
    body = [item for item in query.bodies if item.aggregation is not None]
    assert len(body) == 1
    assert len(repr(body[0].aggregation)) < REPR_LIMIT
