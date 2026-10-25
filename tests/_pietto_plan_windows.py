"""Shared window Project SQL-plan fixtures."""

from _pietto_plan_selected import _roots


SOURCES = {
    "ordinary_selected": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    select:
        id
        w = row_number() window(order by id)
""",
    "named_use": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    let named = window(order by id)
    select:
        id
        w = rank() window named
        w2 = dense_rank() window named
""",
    "selected_and_hidden": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    select:
        id
        w = row_number() window(order by id)
    qualify:
        row_number() window(order by id) <= 3 and w <= 2
""",
    "grouped_satisfying_window": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    group by:
        id
    select:
        total = count()
        w = rank() window(order by total)
    having:
        total > 0
    qualify:
        w <= 3
""",
    "argument_default_partition_order": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
query result:
    from rows
    let alias = value
    select:
        w = lag(alias, 1, id) window(partition by id order by id)
""",
}


def _planned(path, source: str):
    from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), plan
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    assert view.plan is plan
    return roots, plan, checked, view


FAMILIES = (
    ("row_number()", None),
    ("rank()", None),
    ("dense_rank()", None),
    ("percent_rank()", None),
    ("cume_dist()", None),
    ("ntile(3)", None),
    ("lag(value, 2, 0)", None),
    ("lead(value, 0, value)", None),
    ("first_value(value)", "rows between unbounded preceding and current row"),
    ("last_value(value)", "range between unbounded preceding and current row"),
    (
        "nth_value(value, 2) from last ignore nulls",
        "groups between 1 preceding and current row exclude current row",
    ),
)


def _family_source(
    call: str, frame: str | None, named: bool, kind: str, backend: str
) -> str:
    prefix = (
        SOURCES["ordinary_selected"]
        .split("query result:")[0]
        .replace("postgres.table", f"{backend}.table")
    )
    if named:
        body = f"{kind} result:\n    from rows\n    let composed = window base\n    let base = window(\n        order by id desc\n"
        if frame is not None:
            body += f"        {frame}\n"
        return (
            prefix
            + body
            + f"    )\n    select:\n        id\n        w = {call} window composed\n"
        )
    body = f"{kind} result:\n    from rows\n    select:\n        id\n        w = {call} window(\n            order by id desc\n"
    if frame is not None:
        body += f"            {frame}\n"
    return prefix + body + "    )\n"


COMPOSED_SOURCES = {
    "joined_let_where_window": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
source other: Row = postgres.table("other")
query result:
    from rows
    let r = other
    left join r on rows.id == r.id
    let alias = r.value
    where rows.id > 0
    select:
        id = rows.id
        w = lag(alias, 1, 0) window(order by rows.id)
    qualify:
        w > 0
""",
    "joined_hidden_constant": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
source other: Row = postgres.table("other")
query result:
    from rows
    let r = other
    left join r on rows.id == r.id
    select:
        constant = 1
    qualify:
        row_number() window(order by rows.id) <= 3
""",
    "named_windowed_consumer": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
table upstream:
    from rows
    select:
        id
        w = row_number() window(order by id)
query result:
    from upstream
    where w > 0
    select:
        id
        w
""",
    "named_global_then_window": """shape Row:
    id: Int
    value: Int | None
    flag: Bool | None
source rows: Row = postgres.table("rows")
table upstream:
    from rows
    select:
        total = count()
query result:
    from upstream
    select:
        total
        w = row_number() window(order by total)
""",
}
