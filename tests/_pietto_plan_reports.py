"""Shared Project SQL-plan requirement-report fixtures."""

import pytest

from _pietto_plan_aggregate import _group_source, _joined_aggregates
from _pietto_plan_joins import (
    _path_requests,
    _path_source,
    _requests,
    _roots,
    _source as join_source,
)
from _pietto_plan_literals import BODY
from _pietto_plan_results import _source as result_source
from _pietto_plan_row import ROW_BODY, _source as row_source
from _pietto_plan_selected import _source as minimal_source
from _pietto_plan_windows import SOURCES, _family_source
from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_requirements as report
from pietto._project.project_sql_plan_verification import verify_project_sql_plan


P = literals.ProjectSQLLiteralPolicy
F = report.ProjectSQLDemandFamily


def _cases():
    hidden_order = result_source(
        "    select distinct:\n        value\n    order by:\n        hidden\n    limit 0\n"
    ).replace(
        "value: Int nullable", "value: Int not null\n    unique by_value on value"
    )
    right = join_source(
        "inner", "true", tail="    select:\n        id = lhs.id\n"
    ).replace("query result:", "table right_side:")
    right += "table left_side:\n    from lhs\n    select:\n        id\n    limit 0\nquery result:\n    except distinct:\n        from left_side\n        from right_side\n"
    return {
        "minimal": (minimal_source(), None),
        "row": (row_source(ROW_BODY), None),
        "literal_tags": (row_source(BODY), None),
        "join": (join_source("left", "true"), _requests),
        "path": (_path_source(all_unique=True), _path_requests),
        "partial_path": (_path_source(), _path_requests),
        "aggregate": (_joined_aggregates(), None),
        "hidden_group": (_group_source(), None),
        "hidden_window": (SOURCES["selected_and_hidden"], None),
        "window_arguments": (
            _family_source("lag(value, 2, 0)", None, True, "query", "postgres"),
            None,
        ),
        "hidden_order": (hidden_order, None),
        "set_membership": (right, _requests),
        "values": (
            minimal_source().split("query result:")[0]
            + "query result:\n    let seed:\n"
            + "        values(id: Int not null, name: Text nullable):\n"
            + '            1, "a"\n            2, null\n'
            + "    union all:\n        from seed\n        from rows\n",
            None,
        ),
    }


def _reported(roots, policy):
    assert roots[0].ok, roots[0].diagnostics
    plan = sql.build_project_sql_plan(*roots, literal_policy=policy)
    assert isinstance(plan, sql.ProjectSQLPlan), getattr(plan, "blockers", ())
    source = verify_project_sql_plan(plan, *roots, literal_policy=policy)
    assert source.verified, source.issues
    value = report.build_project_sql_requirement_report(source)
    checked = report.verify_project_sql_requirement_report(value, source)
    assert checked.verified, checked.issues
    view = report.inspect_project_sql_requirement_report(checked)
    return roots, plan, source, value, checked, view


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    values = {}
    for name, (source, requests) in _cases().items():
        roots = _roots(tmp_path_factory.mktemp("requirements"), source, requests)
        for policy in P:
            values[name, policy] = _reported(roots, policy)
    return values
