"""Result-boundary emission: visible DISTINCT, relation ORDER carriers, static LIMIT.

Every artifact below is produced by the installed emission path from an ordinary
authored project. A verdict is taken from the published status, the emitted
bytes and the public document, never from a production builder deciding that
its own output is correct.
"""

from copy import copy
from dataclasses import replace
import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project import project_sql_emission_results as resulting
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_rendering import (
    render_join_sql,
    render_row_sql,
)
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
    verify_row_bytes,
    verify_row_query,
)

TARGETS = ("postgres", "mysql")
IDENTIFIER_CASE = {
    "postgres": "quoted_exact",
    "mysql": "lower_case_table_names=0",
}
Q = {"postgres": '"', "mysql": "`"}
UNIQUE_ID = "shape Row:\n    id: Int not null\n    unique by_id on id\n"
RESULT_KINDS = {
    "distinct_quotient",
    "quotient_field_comparison",
    "relation_ordering",
    "order_item",
    "order_null_posture",
    "static_limit",
    "inner_result_boundary",
    "result_terminal_column",
}


def graft(node, **changes):
    changed = copy(node)
    for key, item in changes.items():
        object.__setattr__(changed, key, item)
    return changed


def emit(target, body, *, unique=False):
    """One authored result-boundary body through the installed pipeline."""
    base = probe.fixture(target)
    header = base["source"].split("table result:", 1)[0]
    if unique:
        header = header.replace("shape Row:\n    id: Int not null\n", UNIQUE_ID)
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": IDENTIFIER_CASE[target],
        }
    )
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case",
            header + body,
            probe.encoded(contract).decode(),
            "preserve_literals",
        )
    return outcome


def artifact_of(outcome) -> Any:
    assert outcome.artifact is not None
    return outcome.artifact


def sql_of(outcome) -> str:
    return artifact_of(outcome).rendered.sql.decode()


def blockers(outcome) -> list[str]:
    return [item.detail for item in (outcome.blockers or ())]


def public(outcome) -> dict:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def final_select(sql: str) -> str:
    """The final returning SELECT: everything after the last CTE body closes."""
    depth, start = 0, 0
    for index, char in enumerate(sql):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                start = index + 1
    return sql[start:].strip()


def col(target, alias, name):
    return f"{Q[target]}{alias}{Q[target]}.{Q[target]}{name}{Q[target]}"


def generated(document, kind):
    return [
        item
        for item in document["requirements"]
        if item["denominator"] == "generated" and item["kind"] == kind
    ]


def result_body(outcome) -> Any:
    query = artifact_of(outcome).ast
    bodies = [
        unit
        for unit in getattr(query, "units", query.bodies)
        if type(unit) is resulting.RowResultBody
    ]
    assert bodies, "no result body was emitted"
    return bodies[-1]


DISTINCT_INT = """query result:
    from rows
    select distinct:
        record_id = id
"""


@pytest.mark.parametrize("target", TARGETS)
def test_distinct_is_the_visible_positional_tuple(target):
    """R18: native DISTINCT over exactly the authored visible tuple, after projection."""
    outcome = emit(target, DISTINCT_INT)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    q = Q[target]
    assert final_select(sql) == (
        f"SELECT DISTINCT {col(target, 't0', 'c0')} AS {q}record_id{q}"
        f" FROM {q}p0{q} AS {q}t0{q}"
    )
    # DISTINCT is the result stage, never the projection or the scan.
    assert sql.count("DISTINCT") == 1
    document = public(outcome)
    assert [c["label"] for c in document["columns"]] == ["record_id"]
    (column,) = document["columns"]
    (stage,) = column["correspondence"]["result_origin"]["stages"]
    assert stage["kind"] == "distinct" and stage["quotient_field"] is not None
    assert column["correspondence"]["result_origin"]["terminal"]["kind"] == (
        "result_port"
    )
    assert len(generated(document, "distinct_quotient")) == 1
    assert [r["rule"] for r in generated(document, "quotient_field_comparison")] == [
        "R18"
    ]
    assert [r["subject"]["kind"] for r in generated(document, "distinct_quotient")] == [
        "distinct"
    ]
    body = result_body(outcome)
    assert body.distinct is not None and body.order is None and body.limit is None
    assert [c.read.realization.tag for c in body.columns] == ["Int"]


HIDDEN_WINDOW_DISTINCT = """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 4
"""
HIDDEN_GROUP_DISTINCT = """query result:
    from rows
    group by:
        id
    select distinct:
        total = count()
"""
HIDDEN_ORDER_HELPER = """query result:
    from rows
    select:
        record_id = id
    order by:
        text desc
        id
"""


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "body,label",
    [
        (HIDDEN_WINDOW_DISTINCT, "record_id"),
        (HIDDEN_GROUP_DISTINCT, "total"),
    ],
)
def test_hidden_values_never_enlarge_the_distinct_tuple(target, body, label):
    """C12: a hidden window result or grouping determinant is not a quotient field."""
    outcome = emit(target, body)
    assert outcome.status == "VERIFIED", blockers(outcome)
    final = final_select(sql_of(outcome))
    assert final.startswith("SELECT DISTINCT ")
    assert final.count(" AS ") == 2  # one visible column and the scan alias
    document = public(outcome)
    assert [c["label"] for c in document["columns"]] == [label]
    assert len(generated(document, "quotient_field_comparison")) == 1


@pytest.mark.parametrize("target", TARGETS)
def test_a_hidden_order_helper_never_reaches_the_public_tuple(target):
    """An ORDER key that is not selected is a closed-stage helper, not an output."""
    outcome = emit(target, HIDDEN_ORDER_HELPER)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    q = Q[target]
    assert final_select(sql) == (
        f"SELECT {col(target, 't0', 'c0')} AS {q}record_id{q}"
        f" FROM {q}p0{q} AS {q}t0{q}"
        f" ORDER BY {col(target, 't0', 'c1')} DESC, {col(target, 't0', 'c2')} ASC"
    )
    document = public(outcome)
    assert [c["label"] for c in document["columns"]] == ["record_id"]
    items = generated(document, "order_item")
    assert [i["evidence"][0]["direction"] for i in items] == ["desc", "asc"]
    assert {i["evidence"][0]["carrier"] for i in items} == {"ordinary"}
    assert {i["evidence"][0]["nulls"] for i in items} == {"target_defined"}
    assert "NULLS" not in sql
    # The Text key carries the client-encoding premise; the Int key needs none.
    assert [bool(i["premises"]) for i in items] == [True, False]


@pytest.mark.parametrize("target", TARGETS)
def test_float_distinct_stays_an_upstream_typed_error(target):
    """R18/D07: Float row equivalence is refused upstream; no SQL is built."""
    outcome = emit(
        target,
        "query result:\n    from rows\n    select distinct:\n        r = ratio\n",
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [d.code for d in outcome.diagnostics] == ["PIE-S2339"]
    assert "semantic_result_unsuccessful" in blockers(outcome)
    document = public(outcome)
    assert "sql" not in document and document["artifact"] is None


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "variant,carrier",
    [
        ("order_ordinary", "ordinary"),
        ("order_rebound", "rebound"),
        ("order_completed", "completed"),
    ],
)
def test_the_three_order_carriers_are_realized_separately(target, variant, carrier):
    """R03/R19/C32: ordinary, rebound and completed ORDER keep distinct carriers."""
    item = probe.fixture(target, "O_named_later", variant)
    with tempfile.TemporaryDirectory() as directory:
        checked, outcome = probe.build_case(
            Path(directory) / "case", item["source"], item["contract"], item["policy"]
        )
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    final = final_select(sql)
    assert " ORDER BY " in final and final.count(" ORDER BY ") == 1
    assert re.search(r"ORDER BY \d", sql) is None
    document = public(outcome)
    (order,) = generated(document, "relation_ordering")
    assert order["evidence"] == [{"carrier": carrier, "items": 1}]
    (entry,) = generated(document, "order_item")
    assert entry["evidence"][0]["carrier"] == carrier
    assert entry["evidence"][0]["value_port"]["kind"] == "result_port"
    body = result_body(outcome)
    assert body.order is not None and body.order.carrier == carrier
    plan = cast(Any, checked.plan)
    entry_type = type(plan.bindings.definitions[-1].entry).__name__
    assert (
        entry_type
        == {
            "ordinary": "ProjectIRReusedEffectiveOutput",
            "rebound": "ProjectIRReboundExistingOutput",
            "completed": "ProjectIRCompletedQueryBlockOutput",
        }[carrier]
    )
    if carrier == "rebound":
        assert final.endswith(" LIMIT 1")
        assert body.limit is not None and body.limit.value == 1
        # The rebound ORDER reads the rebuilt active output, not the historical one.
        boundary = body.order.boundary
        entry = plan.bindings.definitions[-1].entry
        assert boundary.properties.ordering.output is not entry.semantic_entry.output
        assert (
            boundary.properties.ordering.items is body.order.order.source.clause.items
        )
    if carrier == "completed":
        assert body.order.boundary.operator.evidence is body.order.order.source


CONSTANT_KEY = """query result:
    from rows
    let:
        one = 1
    select:
        record_id = id
    order by:
        one
        id desc
"""


@pytest.mark.parametrize("target", TARGETS)
def test_a_constant_key_is_an_established_value_never_an_ordinal(target):
    """C10: an established constant port is ordered as a value column."""
    outcome = emit(target, CONSTANT_KEY)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    final = final_select(sql)
    q = Q[target]
    match = re.search(r" ORDER BY (.*)$", final)
    assert match is not None
    keys = match.group(1).split(", ")
    assert len(keys) == 2
    assert keys[0].startswith(f"{q}t0{q}.{q}c") and keys[0].endswith(" ASC")
    assert keys[1].startswith(f"{q}t0{q}.{q}c") and keys[1].endswith(" DESC")
    assert re.search(r"ORDER BY \d", sql) is None
    # The constant value is materialized once, inside the closed stage.
    assert sql.count("CAST(1 AS") == 1
    assert [c["label"] for c in public(outcome)["columns"]] == ["record_id"]


@pytest.mark.parametrize("target", TARGETS)
def test_hidden_strict_fd_order_is_approved_non_support(target):
    """R20: the pending hidden requirement blocks realization; visible keys succeed."""
    hidden = emit(
        target,
        "query result:\n    from rows\n    select distinct:\n        record_id = id\n"
        "    order by:\n        text\n",
        unique=True,
    )
    assert hidden.status == "BLOCKED" and hidden.artifact is None
    assert blockers(hidden) == ["hidden_strict_fd_order_approved_non_support"]
    assert [b.code for b in hidden.blockers] == ["PIE-B1003"]
    assert hidden.diagnostics == ()
    document = public(hidden)
    assert document["blockers"][0]["subject"]["reference"]["kind"] == "order_item"
    visible = emit(
        target,
        "query result:\n    from rows\n    select distinct:\n        record_id = id\n"
        "    order by:\n        id\n",
        unique=True,
    )
    assert visible.status == "VERIFIED", blockers(visible)
    assert final_select(sql_of(visible)).startswith("SELECT DISTINCT ")


@pytest.mark.parametrize("target", TARGETS)
def test_a_computed_order_expression_is_an_exact_typed_blocker(target):
    outcome = emit(
        target,
        "query result:\n    from rows\n    select:\n        record_id = id\n"
        "    order by:\n        id + 1 desc\n",
    )
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == ["order_expression_requires_established_port"]


@pytest.mark.parametrize("target", TARGETS)
def test_float_order_key_is_outside_the_comparison_domain(target):
    outcome = emit(
        target,
        "query result:\n    from rows\n    select:\n        record_id = id\n"
        "    order by:\n        ratio\n",
    )
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == ["order_comparison_domain_unsupported"]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "clause,suffix",
    [("    limit 3\n", " LIMIT 3"), ("    limit 0\n", " LIMIT 0"), ("", "")],
)
def test_static_limit_keeps_absent_zero_and_positive_apart(target, clause, suffix):
    """R21: the exact static value at the result boundary; LIMIT 0 is emitted."""
    outcome = emit(
        target,
        "query result:\n    from rows\n    select:\n        record_id = id\n"
        "    order by:\n        id\n" + clause,
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    final = final_select(sql_of(outcome))
    assert final.endswith(f" ASC{suffix}")
    document = public(outcome)
    limits = generated(document, "static_limit")
    if suffix:
        assert [item["evidence"] for item in limits] == [[{"value": int(suffix[7:])}]]
        assert [item["rule"] for item in limits] == ["R21"]
    else:
        assert limits == []


NESTED = """table top:
    from rows
    select:
        rid = id
    order by:
        id
    limit 1
query result:
    from top
    where rid > 0
    select:
        rid
"""
FILTER_FIRST = """query result:
    from rows
    where id > 0
    select:
        rid = id
    order by:
        id
    limit 1
"""


@pytest.mark.parametrize("target", TARGETS)
def test_an_inner_limit_stays_inside_its_derived_boundary(target):
    """C13: LIMIT before a filter and a filter before LIMIT are different queries."""
    inner = emit(target, NESTED)
    assert inner.status == "VERIFIED", blockers(inner)
    sql = sql_of(inner)
    q = Q[target]
    assert f" ORDER BY {col(target, 't0', 'c1')} ASC LIMIT 1)" in sql
    final = final_select(sql)
    assert "LIMIT" not in final and "ORDER BY" not in final
    # The outer filter is its own stage reading the limited terminal CTE, and
    # the final projection reads that filter stage: LIMIT never moves outward.
    assert f" FROM {q}p1{q} AS {q}s1{q} WHERE " in sql
    assert f"FROM {q}p2{q} AS" in final
    document = public(inner)
    assert [r["rule"] for r in generated(document, "inner_result_boundary")] == ["R21"]
    outer = emit(target, FILTER_FIRST)
    assert outer.status == "VERIFIED", blockers(outer)
    final = final_select(sql_of(outer))
    assert final.endswith(" ASC LIMIT 1") and "WHERE" not in final
    assert "WHERE" in sql_of(outer)


@pytest.mark.parametrize("target", TARGETS)
def test_null_posture_stays_target_defined(target):
    """R19: no NULLS spelling and no discriminator; each target orders natively."""
    outcome = emit(
        target,
        "query result:\n    from rows\n    select:\n        record_id = id\n"
        "        active = flag\n    order by:\n        flag\n        id\n",
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert "NULLS" not in sql and "IS NULL" not in sql and "CASE" not in sql
    document = public(outcome)
    postures = generated(document, "order_null_posture")
    assert len(postures) == 1
    assert postures[0]["evidence"][0]["nulls"] == "target_defined"
    assert [c["label"] for c in document["columns"]] == ["record_id", "active"]


DISTINCT_ORDER_LIMIT = """query result:
    from rows
    select distinct:
        record_id = id
    order by:
        id desc
    limit 2
"""


def _artifact(target, body=DISTINCT_ORDER_LIMIT) -> Any:
    outcome = emit(target, body)
    assert outcome.status == "VERIFIED", blockers(outcome)
    return artifact_of(outcome)


def _with_final(query, body):
    if hasattr(query, "units"):
        return replace(query, units=(*query.units[:-1], body))
    return replace(query, bodies=(*query.bodies[:-1], body))


@pytest.mark.parametrize(
    "mutation",
    [
        "distinct_removed",
        "distinct_added",
        "order_removed",
        "order_item_omitted",
        "order_items_reordered",
        "direction_flipped",
        "null_posture_spelled",
        "port_rebound",
        "hidden_requirement_as_value",
        "limit_removed",
        "limit_changed",
        "limit_zero_deleted",
        "visible_field_omitted",
        "quotient_reordered",
        "float_accepted",
    ],
)
def test_plan_ast_corruptions_are_rejected_independently(mutation):
    """Every mutation contradicts the retained plan; the verifier catches it."""
    artifact = _artifact(
        "postgres",
        "query result:\n    from rows\n    select distinct:\n        record_id = id\n"
        "        active = flag\n    order by:\n        id desc\n        flag\n"
        "    limit 2\n",
    )
    request = artifact.request
    query = artifact.ast
    body = query.bodies[-1]
    assert type(body) is resulting.RowResultBody
    order = body.order
    assert order is not None and body.distinct is not None and body.limit is not None
    plan = request.plan
    if mutation == "distinct_removed":
        changed = replace(body, distinct=None)
    elif mutation == "distinct_added":
        other = _artifact(
            "postgres",
            "query result:\n    from rows\n    select:\n        record_id = id\n"
            "        active = flag\n    order by:\n        id desc\n        flag\n"
            "    limit 2\n",
        )
        plain = other.ast.bodies[-1]
        changed = replace(plain, distinct=body.distinct)
        query, request = other.ast, other.request
    elif mutation == "order_removed":
        changed = replace(body, order=None)
    elif mutation == "order_item_omitted":
        changed = replace(body, order=replace(order, items=order.items[:1]))
    elif mutation == "order_items_reordered":
        first, second = order.items
        changed = replace(
            body,
            order=replace(
                order,
                items=(replace(second, position=0), replace(first, position=1)),
            ),
        )
    elif mutation == "direction_flipped":
        first, second = order.items
        changed = replace(
            body, order=replace(order, items=(replace(first, direction="asc"), second))
        )
    elif mutation == "null_posture_spelled":
        first, second = order.items
        changed = replace(
            body, order=replace(order, items=(first, replace(second, nulls="first")))
        )
    elif mutation == "port_rebound":
        first, second = order.items
        changed = replace(
            body,
            order=replace(
                order,
                items=(
                    replace(first, port=second.port, read=second.read),
                    second,
                ),
            ),
        )
    elif mutation == "hidden_requirement_as_value":
        # A pending requirement now names the first item: the realized value
        # port must be rejected as an unrealizable STRICT-FD requirement.
        pending = SimpleNamespace(item=plan.order_items[0].ref)
        object.__setattr__(plan, "hidden_order_requirements", (pending,))
        changed = body
    elif mutation == "limit_removed":
        changed = replace(body, limit=None)
    elif mutation == "limit_changed":
        changed = replace(body, limit=replace(body.limit, value=3))
    elif mutation == "limit_zero_deleted":
        zero = _artifact(
            "postgres",
            "query result:\n    from rows\n    select:\n        record_id = id\n"
            "    limit 0\n",
        )
        changed = replace(zero.ast.bodies[-1], limit=None)
        query, request = zero.ast, zero.request
    elif mutation == "visible_field_omitted":
        changed = replace(
            body,
            columns=body.columns[:1],
            terminals=body.terminals[:1],
            distinct=replace(body.distinct, fields=body.distinct.fields[:1]),
        )
    elif mutation == "quotient_reordered":
        changed = replace(
            body,
            distinct=replace(
                body.distinct, fields=tuple(reversed(body.distinct.fields))
            ),
        )
    else:
        assert mutation == "float_accepted"
        field = plan.quotient_fields[0]
        object.__setattr__(field.equivalence, "reason", "float_equivalence_deferred")
        changed = body
    grafted = _with_final(query, changed)
    assert not verify_row_query(request, grafted)
    checked = verify_project_sql_emission(replace(artifact, ast=grafted), request)
    assert not checked.verified and "plan_ast_correspondence" in checked.issues


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    [
        "distinct_dropped_from_bytes",
        "direction_swapped_in_bytes",
        "limit_value_changed_in_bytes",
        "key_rendered_as_ordinal",
        "order_by_moved_into_cte",
    ],
)
def test_rendered_byte_corruptions_are_rejected(target, mutation):
    """The byte verifier re-derives every result token; substrings prove nothing."""
    artifact = _artifact(target)
    rendered = artifact.rendered
    sql = rendered.sql.decode()
    q = Q[target]
    if mutation == "distinct_dropped_from_bytes":
        corrupted = sql.replace("SELECT DISTINCT ", "SELECT ", 1)
    elif mutation == "direction_swapped_in_bytes":
        corrupted = sql.replace(" DESC LIMIT", " ASC  LIMIT", 1)
    elif mutation == "limit_value_changed_in_bytes":
        corrupted = sql.replace(" LIMIT 2", " LIMIT 1", 1)
    elif mutation == "key_rendered_as_ordinal":
        corrupted = sql.replace(
            f"ORDER BY {col(target, 't0', 'c0')} DESC", "ORDER BY 1 DESC"
        )
    else:
        assert mutation == "order_by_moved_into_cte"
        corrupted = sql.replace(
            f" ORDER BY {col(target, 't0', 'c0')} DESC LIMIT 2", ""
        ).replace(
            f"AS {q}c0{q} FROM",
            f"AS {q}c0{q} ORDER BY {q}s0{q}.{q}order.id{q} DESC FROM",
        )
    assert corrupted != sql
    changed = replace(rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    checked = verify_project_sql_emission(
        replace(artifact, rendered=changed), artifact.request
    )
    assert not checked.verified and "sql_bytes_or_ranges" in checked.issues


@pytest.mark.parametrize("target", TARGETS)
def test_rendering_is_deterministic_and_verified_from_the_same_ast(target):
    artifact = _artifact(target)
    query = artifact.ast
    again = (render_join_sql if hasattr(query, "units") else render_row_sql)(query)
    assert again.sql == artifact.rendered.sql
    assert verify_row_bytes(query, again)
    document = public(replace_outcome(artifact))
    assert document["sql"] == artifact.rendered.sql.decode()
    kinds = {
        r["kind"] for r in document["requirements"] if r["denominator"] == "generated"
    }
    assert {
        "distinct_quotient",
        "relation_ordering",
        "order_item",
        "static_limit",
    } <= kinds
    # Every generated result requirement names its retained plan subject.
    for item in document["requirements"]:
        if item["denominator"] == "generated" and item["kind"] in RESULT_KINDS:
            assert item["subject"]["kind"] in {
                "distinct",
                "quotient_field",
                "relation_order",
                "order_item",
                "result_limit",
                "result_boundary",
                "result_port",
            }
    ranges = [r["role"] for r in document["ranges"]]
    assert "distinct" in ranges and "order_by" in ranges and "limit_value" in ranges
    assert (
        ranges.index("distinct")
        < ranges.index("order_by")
        < ranges.index("limit_value")
    )


def replace_outcome(artifact: Any):
    from pietto._project.project_sql_emission import EmissionOutcome

    return EmissionOutcome(
        "VERIFIED", artifact.request.verification.completed.diagnostics, artifact
    )


@pytest.mark.parametrize("target", TARGETS)
def test_original_result_demands_carry_their_published_rules(target):
    artifact = _artifact(target)
    document = public(replace_outcome(artifact))
    original = {
        item["subject"]["kind"]: item["rule"]
        for item in document["requirements"]
        if item["denominator"] == "original"
    }
    assert original["distinct"] == "R18"
    assert original["quotient_field"] == "R18"
    assert original["relation_order"] == "R19"
    assert original["order_item"] == "R19"
    assert original["result_limit"] == "R21"
    assert original["result_boundary"] == "R03"


def test_result_body_repr_is_bounded():
    artifact = _artifact("postgres")
    body = artifact.ast.bodies[-1]
    for value in (body, body.distinct, body.order, body.order.items[0], body.limit):
        text = repr(value)
        assert len(text) < 512 and "ProjectSQL" not in text
