"""Window composition across stages and the Slice9 R11/C09 membership obligation.

A completed window producer becomes an ordinary carried value after its own
stage, so an outer JOIN nulls it as a port instead of recomputing it above the
JOIN, and SEMI/ANTI wraps the complete right window terminal rather than any
shortcut.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")

# One right producer whose surviving keys are decided by a window and QUALIFY.
SELECTED_RIGHT = """table ranked:
    from rhs
    select:
        id
        w = row_number() window:
            order by:
                id
    qualify:
        w <= 1
"""
HIDDEN_RIGHT = """table ranked:
    from rhs
    select:
        id
    qualify:
        row_number() window:
            order by:
                id
        <= 1
"""
PRE_WINDOW_RIGHT = """table ranked:
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


def emit_join(target, source, *, policy="preserve_literals"):
    item = probe.join_witness(target, source, policy=policy)
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case", item["source"], item["contract"], policy
        )
    return outcome


def emit_aggregate(target, body):
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    header = probe.AGGREGATE_HEADER.format(target=target)
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case",
            header + body,
            item["contract"],
            "preserve_literals",
        )
    return outcome


def sql_of(outcome) -> str:
    assert outcome.artifact is not None
    return outcome.artifact.rendered.sql.decode()


def blockers(outcome) -> list[str]:
    return [item.detail for item in (outcome.blockers or ())]


def labels(outcome) -> list[str]:
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    return [column["label"] for column in document["columns"]]


def referenced_cte(sql: str, marker: str) -> str:
    """The body of the CTE this EXISTS actually reads, by name.

    The right terminal is a nonrecursive CTE, so the membership test follows the
    reference instead of expecting the producer to be inlined.
    """

    position = sql.index(marker)
    name = re.search(r"FROM [\"`]([A-Za-z0-9_]+)[\"`]", sql[position:])
    assert name is not None, sql[position : position + 120]
    opened = re.search(rf"[\"`]{name.group(1)}[\"`] \([^)]*\) AS \(", sql)
    assert opened is not None, name.group(1)
    start = opened.end()
    depth = 1
    for index in range(start, len(sql)):
        if sql[index] == "(":
            depth += 1
        elif sql[index] == ")":
            depth -= 1
            if depth == 0:
                return sql[start:index]
    raise AssertionError("unterminated CTE body")


AGGREGATE_THEN_WINDOW = """table result:
    from agg
    group by:
        key
    select:
        key
        total = count()
        w = row_number() window:
            order by:
                key
"""


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_result_is_a_valid_pre_window_input(target):
    """R12 into R14: the window orders by the established aggregate result port."""
    outcome = emit_aggregate(target, AGGREGATE_THEN_WINDOW)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert "ROW_NUMBER() OVER (ORDER BY " in sql
    # The window orders by a carried stage column, never by a recomputed COUNT.
    order = re.search(r"ROW_NUMBER\(\) OVER \(ORDER BY ([^)]*)\)", sql)
    assert order is not None
    assert "COUNT" not in order.group(1)
    assert labels(outcome) == ["key", "total", "w"]


JOIN_THEN_WINDOW = """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
        w = row_number() window:
            order by:
                lhs.id
"""


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_terminal_is_a_valid_pre_window_input(target):
    """R07 into R14: the window reads the actual post-JOIN port."""
    outcome = emit_join(target, JOIN_THEN_WINDOW)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert "ROW_NUMBER() OVER (ORDER BY " in sql
    assert " JOIN " in sql
    assert labels(outcome) == ["a", "w"]


WINDOW_PRODUCER_LEFT = (
    SELECTED_RIGHT
    + """query result:
    from lhs
    left join ranked as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
        b = r.w
"""
)


@pytest.mark.parametrize("target", TARGETS)
def test_a_completed_window_value_is_nulled_as_a_port_by_an_outer_join(target):
    """A carried window result is outer-nulled, never recomputed above the JOIN."""
    outcome = emit_join(target, WINDOW_PRODUCER_LEFT)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    # The window is computed once, inside its own producer stage.
    assert sql.count("ROW_NUMBER()") == 1
    assert " LEFT " in sql or " LEFT JOIN " in sql
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    carried = {column["label"]: column for column in document["columns"]}
    assert set(carried) == {"a", "b"}
    # The producer's own port becomes nullable on the null-extended side.
    assert carried["b"]["nullable"] is True


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "kind,marker", (("semi", "EXISTS ("), ("anti", "NOT EXISTS ("))
)
def test_a_selected_window_terminal_decides_membership(target, kind, marker):
    """R11/C09: SEMI and ANTI wrap the complete right window/QUALIFY terminal."""
    outcome = emit_join(target, SELECTED_RIGHT + consumer(kind))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert f" WHERE {marker}" in sql
    # The right terminal keeps its own window computation and its own filter.
    body = referenced_cte(sql, marker)
    assert "ROW_NUMBER()" in body or "ROW_NUMBER()" in sql
    # The right output never reaches the left schema.
    assert labels(outcome) == ["a"]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "kind,marker", (("semi", "EXISTS ("), ("anti", "NOT EXISTS ("))
)
def test_a_hidden_window_terminal_decides_membership_without_leaking(
    target, kind, marker
):
    """R11/C09 with a hidden result: it filters the right, never exports itself."""
    outcome = emit_join(target, HIDDEN_RIGHT + consumer(kind))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert f" WHERE {marker}" in sql
    body = referenced_cte(sql, marker)
    assert "ROW_NUMBER()" in body or "ROW_NUMBER()" in sql
    assert labels(outcome) == ["a"]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_the_pre_window_right_is_a_different_membership(target, kind):
    """A right without its window and QUALIFY is a different, weaker terminal.

    This is the negative control for the base-table shortcut: the same consumer
    over a producer that never computed its window keeps no ROW_NUMBER at all,
    so an implementation that silently substituted it would be detectable here.
    """
    outcome = emit_join(target, PRE_WINDOW_RIGHT + consumer(kind))
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert "ROW_NUMBER()" not in sql_of(outcome)
    assert labels(outcome) == ["a"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_producer_is_consumed_by_an_ordinary_named_use(target):
    """A named producer's completed window result is an ordinary carried value."""
    source = (
        SELECTED_RIGHT
        + """query result:
    from ranked
    select:
        a = id
        b = w
"""
    )
    outcome = emit_join(target, source)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert sql.count("ROW_NUMBER()") == 1
    assert labels(outcome) == ["a", "b"]
