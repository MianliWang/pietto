"""R03 ORDER/LIMIT sharing, R11/C09 LIMIT membership and Slice9 composition.

A definition with result boundaries is a complete terminal producer: every
named use, JOIN input and SEMI/ANTI right side binds its post-DISTINCT/ORDER/
LIMIT output, never its projection or its source. The window, QUALIFY and
aggregate stages of Slice8/9 are consumed as established ports and keep their
own meaning.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project import project_sql_emission_results as resulting
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")
IDENTIFIER_CASE = {
    "postgres": "quoted_exact",
    "mysql": "lower_case_table_names=0",
}
Q = {"postgres": '"', "mysql": "`"}

LIMIT1_RIGHT = """table ranked:
    from rhs
    select:
        id
    order by:
        id
    limit 1
"""
LIMIT0_RIGHT = """table ranked:
    from rhs
    select:
        id
    limit 0
"""
UNORDERED_RIGHT = """table ranked:
    from rhs
    select:
        id
"""


def consumer(kind):
    return f"""query result:
    from lhs
    {kind} join ranked as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
"""


def emit_join(target, source):
    item = probe.join_witness(target, source)
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case",
            item["source"],
            item["contract"],
            "preserve_literals",
        )
    return outcome


def emit(target, body):
    base = probe.fixture(target)
    header = base["source"].split("table result:", 1)[0]
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


def document(outcome) -> dict:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def labels(outcome) -> list[str]:
    return [column["label"] for column in document(outcome)["columns"]]


def cte_bodies(sql: str) -> dict[str, str]:
    """Every generated CTE body by name, following the actual WITH list."""
    bodies = {}
    for match in re.finditer(r"[\"`]([a-z][0-9]+)[\"`] \([^)]*\) AS \(", sql):
        start = match.end()
        depth = 1
        for index in range(start, len(sql)):
            if sql[index] == "(":
                depth += 1
            elif sql[index] == ")":
                depth -= 1
                if depth == 0:
                    bodies[match.group(1)] = sql[start:index]
                    break
    return bodies


def membership_source(sql: str, marker: str) -> str:
    """The relation the EXISTS subquery actually reads."""
    position = sql.index(marker)
    match = re.search(r"FROM [\"`]([a-z][0-9]+)[\"`]", sql[position:])
    assert match is not None, sql[position : position + 160]
    return match.group(1)


def units(outcome) -> Any:
    query = artifact_of(outcome).ast
    return getattr(query, "units", query.bodies)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "kind,marker", (("semi", "EXISTS ("), ("anti", "NOT EXISTS ("))
)
def test_a_right_limit_zero_terminal_decides_membership(target, kind, marker):
    """R11/C09: the right side is the complete post-LIMIT terminal, kept LIMIT 0."""
    outcome = emit_join(target, LIMIT0_RIGHT + consumer(kind))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert f" WHERE {marker}" in sql
    body = cte_bodies(sql)[membership_source(sql, marker)]
    assert body.endswith(" LIMIT 0")
    assert "ORDER BY" not in body
    assert labels(outcome) == ["a"]
    generated = [
        r["kind"]
        for r in document(outcome)["requirements"]
        if r["denominator"] == "generated"
    ]
    assert "complete_right_terminal" in generated and "static_limit" in generated
    producer = [u for u in units(outcome) if type(u) is resulting.RowResultBody]
    assert len(producer) == 1 and producer[0].limit is not None
    assert producer[0].limit.value == 0 and not producer[0].final


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "kind,marker", (("semi", "EXISTS ("), ("anti", "NOT EXISTS ("))
)
def test_a_right_ordered_limit_one_terminal_decides_membership(target, kind, marker):
    """R11/C09: ORDER + LIMIT 1 selects one key; membership wraps that terminal."""
    outcome = emit_join(target, LIMIT1_RIGHT + consumer(kind))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert f" WHERE {marker}" in sql
    q = Q[target]
    body = cte_bodies(sql)[membership_source(sql, marker)]
    assert re.search(rf" ORDER BY {q}t0{q}\.{q}c1{q} ASC LIMIT 1$", body)
    assert labels(outcome) == ["a"]
    control = emit_join(target, UNORDERED_RIGHT + consumer(kind))
    assert control.status == "VERIFIED", blockers(control)
    assert "LIMIT" not in sql_of(control) and "ORDER BY" not in sql_of(control)
    assert not any(type(u) is resulting.RowResultBody for u in units(control))


@pytest.mark.parametrize("target", TARGETS)
def test_a_membership_right_side_never_short_circuits_the_result_body(target):
    """A right producer bound to its projection instead of its terminal is rejected."""
    from dataclasses import replace

    from pietto._project.project_sql_emission_verification import verify_row_query

    outcome = emit_join(target, LIMIT1_RIGHT + consumer("semi"))
    assert outcome.status == "VERIFIED", blockers(outcome)
    artifact = artifact_of(outcome)
    query = artifact.ast
    all_units = list(query.units)
    (result,) = [u for u in all_units if type(u) is resulting.RowResultBody]
    (join,) = [u for u in all_units if hasattr(u, "membership")]
    right = join.inputs[1]
    shortcut = replace(
        join,
        inputs=(
            join.inputs[0],
            replace(
                right,
                producer=result.scan.body,
                columns=tuple(
                    replace(column, terminal=read.column.terminal)
                    for column, read in zip(right.columns, result.scan.body.columns)
                ),
            ),
        ),
    )
    all_units[all_units.index(join)] = shortcut
    assert not verify_row_query(
        artifact.request, replace(query, units=tuple(all_units))
    )


SHARED_ORDER_LIMIT = """table top:
    from rows
    select:
        rid = id
    order by:
        id
    limit 2
query result:
    from top
    inner join top as r:
        from top
        on top.rid == r.rid
    select:
        a = top.rid
        b = r.rid
"""


@pytest.mark.parametrize("target", TARGETS)
def test_one_ordered_limited_producer_is_shared_by_two_uses(target):
    """R03/C19: one definition, two uses, each bound to the post-LIMIT terminal."""
    outcome = emit(target, SHARED_ORDER_LIMIT)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    q = Q[target]
    bodies = cte_bodies(sql)
    ordered = [name for name, body in bodies.items() if body.endswith(" LIMIT 2")]
    assert len(ordered) == 1, bodies
    (name,) = ordered
    assert f" ORDER BY {q}t0{q}.{q}c1{q} ASC LIMIT 2" in bodies[name]
    # Both JOIN inputs read the same terminal CTE, never the projection or source.
    assert sql.count(f"FROM {q}{name}{q} AS") + sql.count(f"JOIN {q}{name}{q} AS") == 2
    assert sql.count(" LIMIT ") == 1 and sql.count(" ORDER BY ") == 1
    assert labels(outcome) == ["a", "b"]
    results = [u for u in units(outcome) if type(u) is resulting.RowResultBody]
    assert len(results) == 1 and not results[0].final
    (join,) = [u for u in units(outcome) if hasattr(u, "membership")]
    assert all(item.producer is results[0] for item in join.inputs)
    assert all(
        column.terminal is read.column.terminal
        for item in join.inputs
        for column, read in zip(item.columns, results[0].columns, strict=True)
    )


QUALIFY_THEN_DISTINCT = """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 4
"""
SELECTED_WINDOW_ORDER = """query result:
    from rows
    select:
        record_id = id
        n = row_number() window:
            order by:
                id
    order by:
        n desc
    limit 2
"""
QUALIFY_ORDER_LIMIT = """query result:
    from rows
    select distinct:
        record_id = id
    qualify:
        row_number() window:
            order by:
                id
        <= 3
    order by:
        id desc
    limit 2
"""


@pytest.mark.parametrize("target", TARGETS)
def test_qualify_feeds_distinct_without_exposing_the_hidden_window(target):
    outcome = emit(target, QUALIFY_THEN_DISTINCT)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert sql.count("ROW_NUMBER()") == 1
    final = sql[sql.rindex(") ") + 2 :]
    assert final.startswith("SELECT DISTINCT ") and "ROW_NUMBER" not in final
    assert labels(outcome) == ["record_id"]
    body = [u for u in units(outcome) if type(u) is resulting.RowResultBody][-1]
    assert body.distinct is not None and len(body.distinct.fields) == 1


@pytest.mark.parametrize("target", TARGETS)
def test_a_selected_window_result_is_an_ordinary_relation_order_key(target):
    """Relation ORDER over an established window port is not window ORDER."""
    outcome = emit(target, SELECTED_WINDOW_ORDER)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    q = Q[target]
    final = sql[sql.rindex(") ") + 2 :]
    assert re.search(rf" ORDER BY {q}t0{q}\.{q}c\d+{q} DESC LIMIT 2$", final)
    # The window's own ORDER stays inside OVER (...); the relation ORDER is
    # the final SELECT's, and neither is rewritten into the other.
    assert "OVER (ORDER BY " in sql and sql.count("ORDER BY ") == 2
    assert labels(outcome) == ["record_id", "n"]
    body = [u for u in units(outcome) if type(u) is resulting.RowResultBody][-1]
    assert body.order is not None
    (item,) = body.order.items
    assert item.read.window is not None and item.read.realization.tag == "Int"


@pytest.mark.parametrize("target", TARGETS)
def test_qualify_then_distinct_order_limit_keeps_the_stage_law(target):
    outcome = emit(target, QUALIFY_ORDER_LIMIT)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    final = sql[sql.rindex(") ") + 2 :]
    assert final.startswith("SELECT DISTINCT ") and final.endswith(" DESC LIMIT 2")
    body = [u for u in units(outcome) if type(u) is resulting.RowResultBody][-1]
    assert [b.kind.value for b in body.boundaries] == [
        "distinct",
        "relation_ordering",
        "limit",
    ]
    assert body.scan.body.block.kind.value == "projection"
    # Stage law: the QUALIFY filter precedes the projection the result reads.
    kinds = [u.block.kind.value for u in units(outcome) if hasattr(u, "index")]
    assert kinds.index("qualify") < kinds.index("projection")
    assert labels(outcome) == ["record_id"]


@pytest.mark.parametrize("target", TARGETS)
def test_an_ordinary_named_use_reads_the_post_limit_terminal(target):
    outcome = emit(
        target,
        "table top:\n    from rows\n    select:\n        rid = id\n    order by:\n"
        "        id desc\n    limit 1\nquery result:\n    from top\n    select:\n"
        "        a = rid\n",
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    bodies = cte_bodies(sql)
    limited = [name for name, body in bodies.items() if body.endswith(" LIMIT 1")]
    assert len(limited) == 1
    final = sql[sql.rindex(") ") + 2 :]
    q = Q[target]
    assert f"FROM {q}{limited[0]}{q} AS" in final
    assert "LIMIT" not in final and "ORDER BY" not in final
    assert labels(outcome) == ["a"]
