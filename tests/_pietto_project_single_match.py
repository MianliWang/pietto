"""Authored project single-match request fixtures."""

from _pietto_project_join import _source
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_single_match import ProjectSingleMatchRequest


def _request(
    completed: ProjectConcreteCompletedSemanticResult, position: int = 0
) -> ProjectSingleMatchRequest:
    condition = completed.roots.join_conditions.entries[position]
    return ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)


def _limited_source(
    *, right_limit: int | None, post_limit: bool = False, where: bool = False
) -> str:
    source = _source("true").split("query result:", 1)[0]
    source += "table right_named:\n    from rhs\n    select:\n        id\n"
    if right_limit is not None:
        source += f"    limit {right_limit}\n"
    source += "query result:\n    from lhs\n    inner join right_named as r:\n        from lhs\n        on true\n"
    if where:
        source += "    where lhs.id == 1\n"
    source += "    select:\n        id = lhs.id\n"
    if post_limit:
        source += "    limit 1\n"
    return source


def _asymmetric_source(*, target_unique: bool, source_unique: bool = False) -> str:
    return f"""shape LeftRow:
    id: Int not null
{("    unique key on id" + chr(10)) if source_unique else ""}shape RightRow:
    id: Int not null
{("    unique key on id" + chr(10)) if target_unique else ""}source lhs: LeftRow is postgres.table("lhs")
source rhs: RightRow is postgres.table("rhs")
relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on l.id == r.id
query result:
    from lhs
    inner join rhs as r:
        from lhs
    select:
        id = lhs.id
"""
