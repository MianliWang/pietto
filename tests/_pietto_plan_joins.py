"""Shared JOIN planning fixtures."""

from dataclasses import replace
from pathlib import Path

from _pietto_project_join import _completed, _source as _upstream_source
from _pietto_project_single_match import _asymmetric_source
from pietto._project.project_completed_semantics import (
    with_project_single_match_requests,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchScope,
)
from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan


def _source(
    kind="inner",
    predicate="lhs.id == r.id",
    *,
    family="postgres",
    owner="query",
    tail=None,
):
    source = (
        _upstream_source(None if kind == "cross" else predicate, kind=kind)
        .replace("postgres.table", family + ".table")
        .replace("query result:", owner + " result:")
    )
    if tail is not None:
        source = source.replace("    select:\n        id = lhs.id\n", tail)
    elif kind not in {"semi", "anti"}:
        source += "        right_id = r.id\n"
    return source


def _roots(path: Path, source: str, requests=None):
    completed = _completed(path, source)
    if requests is not None:
        completed = with_project_single_match_requests(completed, requests(completed))
    snapshot = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(snapshot)
    assert checked.verified, checked.issues
    bundle = build_project_query_block_ir_analysis_bundle(checked)
    selected = tuple(
        owner for owner in snapshot.owners if owner.definition.name == "result"
    )
    assert len(selected) == 1
    return completed, bundle, selected[0]


def _product(path: Path, source: str, requests=None):
    roots = _roots(path, source, requests)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    return roots, plan, inspect_project_sql_plan(checked)


def _requests(completed):
    return tuple(
        ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)
        for condition in completed.roots.join_conditions.entries
    )


def _path_source(kind="inner", *, all_unique=False):
    source = _asymmetric_source(target_unique=True, source_unique=all_unique).replace(
        "inner join rhs as r:", kind + " join lhs as r:"
    )
    return source.replace(
        "        from lhs\n    select:",
        "        from lhs\n        via link: l -> r\n        via link: r -> l\n    select:",
    )


def _path_requests(completed):
    condition = completed.roots.join_conditions.entries[0]
    path = condition.effective_use.path
    assert path is not None
    request = ProjectSingleMatchRequest(
        owner=condition.use.owner, use=condition.use, path=path
    )
    return tuple(
        replace(request, scope=ProjectSingleMatchScope.PATH_HOP, hop=step)
        for step in path.steps
    ) + (replace(request, scope=ProjectSingleMatchScope.WHOLE_PATH),)
