"""Shared named-producer Project SQL-plan fixtures."""

from _pietto_plan_selected import _source


def _chain(kind: str = "table", family: str = "postgres") -> str:
    base = _source(family=family).split("query result:", 1)[0]
    return (
        base
        + f"""{kind} first:
    from rows
    select:
        a = name
        b = name
        key = id
table second:
    from first
    select:
        renamed = b
        id = key
query result:
    from second
    select:
        id
        value = renamed
"""
    )


def _binding_product(roots):
    from pietto._project.project_sql_plan import (
        ProjectSQLBindings,
        build_project_sql_bindings,
    )
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_bindings
    from pietto._project.project_sql_plan_verification import (
        verify_project_sql_bindings,
    )

    bindings = build_project_sql_bindings(*roots)
    assert isinstance(bindings, ProjectSQLBindings)
    verified = verify_project_sql_bindings(bindings, *roots)
    assert verified.verified, verified.issues
    return bindings, inspect_project_sql_bindings(verified)


def _repeated_sets(depth: int = 12) -> str:
    text = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
table p0:
    from rows
    select:
        id
"""
    text += "".join(
        f"table p{i}:\n    union all:\n        from p{i - 1}\n        from p{i - 1}\n"
        for i in range(1, depth + 1)
    )
    return text + f"query result:\n    from p{depth}\n    select:\n        id\n"
