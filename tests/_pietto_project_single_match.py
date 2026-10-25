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
    source = _source("True").split("query result:", 1)[0]
    source += "table right_named:\n    from rhs\n    select:\n        id\n"
    if right_limit is not None:
        source += f"    limit {right_limit}\n"
    source += "query result:\n    from lhs\n    let r = right_named\n    inner join r on True\n"
    if where:
        source += "    where lhs.id == 1\n"
    source += "    select:\n        id = lhs.id\n"
    if post_limit:
        source += "    limit 1\n"
    return source


def _asymmetric_source(*, target_unique: bool, source_unique: bool = False) -> str:
    return f"""shape LeftRow:
    id: Int
{("    key = unique(id)" + chr(10)) if source_unique else ""}shape RightRow:
    id: Int
{("    key = unique(id)" + chr(10)) if target_unique else ""}source lhs: LeftRow = postgres.table("lhs")
source rhs: RightRow = postgres.table("rhs")
relationship Link(l: LeftRow, r: RightRow):
    l.id == r.id
query result:
    from lhs
    let r = rhs
    inner join r on Link(lhs, r)
    select:
        id = lhs.id
"""
