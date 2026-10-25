"""Shared binding fixtures for execution-layer tests."""

import textwrap
from dataclasses import replace

from _pietto_execution_postgres_rows_probe import template as template


def bind(template_, *values):
    from pietto._project import project_execution_template as binding

    return binding.bind_values(
        template_, tuple(zip(template_.slots, values, strict=True))
    )


def proof_artifact(directory, *, proved=True, retained: bool | str = False):
    import _pietto_sql_emission as probe
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import (
        ProjectSingleMatchRequest,
        ProjectSingleMatchAssessment,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_emission import emit_project_sql

    source = """table ranked:
    from rhs
    select:
        id
    limit 1
query result:
    from lhs
    let r = ranked
    inner join r on lhs.id == r.id and lhs.id > 1
    select:
        value = lhs.id
"""
    if retained:
        unused = source.split("query result:", 1)[1]
        if retained == "let":
            # The unselected request owner is a relation let of `unused`.
            unused = (
                "\n    let j:"
                + textwrap.indent(unused, "    ")
                + "    from j\n    select:\n        value\n"
            )
        elif retained == "capture":
            # The unselected request owner reads a capturing let by EXISTS.
            unused = (
                "\n    let m:\n        capture lhs\n        from rhs\n"
                "        where rhs.id == lhs.id\n        select:\n            id"
                + unused.replace("    select:\n", "    where exists m\n    select:\n")
            )
        elif retained == "lateral":
            # The unselected request owner joins a capturing let LATERAL.
            unused = (
                "\n    let m:\n        capture lhs\n        from rhs\n"
                "        where rhs.id == lhs.id\n        select:\n            id"
                + unused.replace(
                    "    select:\n",
                    "    let x = m\n    inner join x on x.id == lhs.id\n    select:\n",
                )
            )
        source += "query unused:" + unused
    if not proved:
        source = source.replace("    limit 1\n", "")
    item = probe.join_witness("postgres", source, policy="bind_safe_literals")
    checked, _ = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    completed = checked.completed
    requests = []
    for condition in completed.roots.join_conditions.entries:
        request = ProjectSingleMatchRequest(
            owner=condition.use.owner, use=condition.use, condition=condition
        )
        assessment = ProjectSingleMatchAssessment(
            root=completed.effective_outputs, request=request
        )
        requests.append(replace(request, input_pairs=assessment.input_pairs))
    completed = with_project_single_match_requests(completed, tuple(requests))
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    (selected,) = tuple(
        owner for owner in ir.owners if owner.definition.name == "result"
    )
    policy = checked.literal_policy
    plan = build_project_sql_plan(completed, bundle, selected, literal_policy=policy)
    checked = verify_project_sql_plan(
        plan, completed, bundle, selected, literal_policy=policy
    )
    return emit_project_sql(checked, item["contract"].encode())
