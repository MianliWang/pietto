"""Explicit original single-match inputs; no database work at import time."""

from dataclasses import replace
import json

import _pietto_phase66_sql_emission_probe as emission


DIRECT = """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    select:
        left_id = lhs.id
        right_key = r.key
"""


def planned(
    directory,
    target="postgres",
    body: str | dict[str, str] = DIRECT,
    *,
    requested=True,
    copies=1,
    policy="preserve_literals",
    scope="direct",
    link=False,
    right_unique=False,
    wide_text=False,
):
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import (
        ProjectSingleMatchRequest,
        ProjectSingleMatchAssessment,
        ProjectSingleMatchScope,
    )
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    fixture = emission.join_witness(
        target,
        body,
        policy=policy,
        link=link,
        module="a.pietto" if type(body) is dict else None,
    )
    if wide_text:
        fixture["source"] = fixture["source"].replace(
            "key: Int nullable", "key: Text nullable"
        )
        contract = json.loads(fixture["contract"])
        for source in contract["sources"]:
            source["relation"]["name"] = "p68_guard_wide_" + source["selector"]["name"]
            source["fields"][1]["representation"] = {
                "storage": {"kind": "my_varchar", "length": 1024}
                if target == "mysql"
                else {"kind": "pg_text"},
                "nullable": True,
                "domain": {
                    "kind": "text",
                    "max_characters": 1024,
                    "encoding": "utf8mb4" if target == "mysql" else "UTF8",
                    "collation": "utf8mb4_0900_bin" if target == "mysql" else "C",
                    "padding": "NO PAD",
                },
            }
        fixture["contract"] = json.dumps(contract)
    if right_unique:
        fixture["source"] = (
            fixture["source"]
            .replace(
                "source lhs:",
                "shape RightRow:\n    id: Int not null\n    key: Int nullable\n    unique key on id\nsource lhs:",
            )
            .replace("source rhs: Row", "source rhs: RightRow")
        )
    checked, _ = emission.build_case(
        directory, fixture["source"], fixture["contract"], policy
    )
    if not requested:
        return checked, fixture["contract"].encode()
    completed = checked.completed
    requests = []
    for condition in completed.roots.join_conditions.entries:
        for _ in range(copies):
            request = ProjectSingleMatchRequest(
                owner=condition.use.owner, use=condition.use, condition=condition
            )
            if scope != "direct":
                path = condition.effective_use.path
                if path is None:
                    raise ValueError("guard fixture missing original path")
                request = replace(
                    request,
                    scope=ProjectSingleMatchScope.WHOLE_PATH
                    if scope == "whole"
                    else ProjectSingleMatchScope.PATH_HOP,
                    path=path,
                    hop=None if scope == "whole" else path.steps[int(scope[-1])],
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
    (owner,) = tuple(o for o in ir.owners if o.definition.name == "result")
    plan = build_project_sql_plan(
        completed, bundle, owner, literal_policy=checked.literal_policy
    )
    verified = verify_project_sql_plan(
        plan, completed, bundle, owner, literal_policy=checked.literal_policy
    )
    if not verified.verified:
        raise ValueError("original guarded fixture plan")
    return verified, fixture["contract"].encode()


# Literal oracle rows are authored from match/visibility laws, not guard SQL.
LHS = ((1, None), (1, 7), (2, None))
ONE = ((1, None),)
TWO = ((1, None), (1, None))
PATH = """query result:
    from lhs
    inner join lhs as r:
        from lhs
        via link: l -> r
        via link: r -> l
    select:
        left_id = lhs.id
        right_key = r.key
"""


def manifest():
    """Named mechanisms with literal full results; no result-count oracle."""
    records = []

    def add(
        name,
        body: str | dict[str, str] = DIRECT,
        *,
        lhs=LHS,
        rhs=ONE,
        rows=((1, None), (1, None)),
        states=("FULFILLED",),
        **options,
    ):
        records.append(
            dict(
                name=name,
                body=body,
                lhs=lhs,
                rhs=rhs,
                rows=rows,
                states=states,
                options=options,
            )
        )

    add("bag_one")
    add("source_text_wide", rhs=((1, "v"),), rows=((1, "v"), (1, "v")), wide_text=True)
    add("bag_zero", rhs=(), rows=())
    add("bag_two_equal_null", rhs=TWO, rows=(), states=("VIOLATED",))
    add(
        "left_unmatched",
        DIRECT.replace("inner join", "left join"),
        rhs=(),
        rows=((1, None), (1, None), (2, None)),
    )
    add(
        "right_unmatched",
        DIRECT.replace("inner join", "right join"),
        lhs=(),
        rhs=((9, None),),
        rows=((None, None),),
    )
    add(
        "full_unmatched",
        DIRECT.replace("inner join", "full join"),
        lhs=((1, None),),
        rhs=((9, None),),
        rows=((1, None), (None, None)),
        postgres_only=True,
    )
    for kind in ("semi", "anti"):
        body = DIRECT.replace("inner join", kind + " join").replace(
            "        right_key = r.key\n", ""
        )
        add(kind + "_does_not_prove", body, rhs=TWO, rows=(), states=("VIOLATED",))
    add(
        "predicate_false",
        DIRECT.replace("on lhs.id == r.id", "on lhs.id == r.id and false"),
        rhs=TWO,
        rows=(),
    )
    add(
        "predicate_unknown",
        DIRECT.replace("on lhs.id == r.id", "on lhs.id == r.id and r.key > 0"),
        rhs=TWO,
        rows=(),
    )
    for name, body in (
        (
            "hidden_where",
            DIRECT.replace("    select:", "    where lhs.id < 0\n    select:"),
        ),
        ("hidden_limit_zero", DIRECT + "    limit 0\n"),
        ("hidden_distinct", DIRECT.replace("    select:", "    select distinct:")),
    ):
        add(name, body, rhs=TWO, rows=(), states=("VIOLATED",))
    for limit in (0, 1):
        body = (
            "table right_named:\n    from rhs\n    select:\n        id\n        key\n    limit "
            + str(limit)
            + "\n"
            + DIRECT.replace("join rhs as r", "join right_named as r")
        )
        add(
            "right_limit_" + str(limit),
            body,
            rhs=TWO,
            rows=() if limit == 0 else ((1, None), (1, None)),
            states=("STATIC",),
            allow=False,
        )
    add("no_request", requested=False, states=(), allow=False)
    add(
        "forbidden_pending",
        rows=(),
        states=("UNKNOWN",),
        allow=False,
        failure="GUARD_SQL_FORBIDDEN_UNFULFILLED",
    )
    add("two_requests", copies=2, states=("FULFILLED", "FULFILLED"))
    add(
        "two_requests_violated",
        copies=2,
        rhs=TWO,
        rows=(),
        states=("VIOLATED", "VIOLATED"),
    )
    for scope, states, rows in (
        ("whole", ("FULFILLED", "VIOLATED"), ()),
        ("hop0", ("FULFILLED",), ((1, None),) * 4),
        ("hop1", ("VIOLATED",), ()),
    ):
        add(
            "path_" + scope,
            PATH,
            lhs=((1, None), (1, None)),
            scope=scope,
            link=True,
            states=states,
            rows=rows,
        )
    relation = DIRECT.replace(
        "        on lhs.id == r.id\n", "        via link: l -> r\n"
    )
    add("relationship_fact", relation, link=True, right_unique=True)
    add(
        "relationship_fact_false",
        relation,
        link=True,
        right_unique=True,
        rhs=TWO,
        rows=(),
        states=("VIOLATED",),
    )
    add(
        "case_labels",
        DIRECT.replace("left_id =", "Key =").replace("right_key =", "key ="),
    )
    add("refined_pages", refined=True)
    add(
        "refined_violation_outside_page",
        lhs=((1, None), (2, None)),
        rhs=((1, None), (2, None), (2, None)),
        rows=(),
        states=("VIOLATED",),
        refined=True,
        page_size=1,
    )
    add(
        "path_whole_positive",
        PATH,
        lhs=((1, None),),
        scope="whole",
        link=True,
        states=("FULFILLED", "FULFILLED"),
        rows=((1, None),),
    )
    add(
        "path_first_violation_hidden",
        PATH + "    limit 0\n",
        lhs=((1, None),),
        rhs=TWO,
        scope="whole",
        link=True,
        states=("VIOLATED", "FULFILLED"),
        rows=(),
    )
    add(
        "path_later_violation_hidden",
        PATH.replace("    select:", "    where lhs.id < 0\n    select:"),
        lhs=((1, None), (1, None)),
        scope="whole",
        link=True,
        states=("FULFILLED", "VIOLATED"),
        rows=(),
    )
    add(
        "path_refined",
        PATH,
        lhs=((1, None),),
        scope="whole",
        link=True,
        states=("FULFILLED", "FULFILLED"),
        rows=((1, None),),
        refined=True,
    )
    global_right = (
        "table right_named:\n    from rhs\n    select:\n        id = count()\n        key = min(key)\n"
        + DIRECT.replace("join rhs as r", "join right_named as r")
    )
    add(
        "right_global",
        global_right,
        rhs=TWO,
        rows=((2, None),),
        states=("STATIC",),
        allow=False,
    )
    qualify = (
        DIRECT
        + "    qualify:\n        row_number() window:\n            order by:\n                lhs.id\n        <= 0\n"
    )
    add("hidden_qualify", qualify, rhs=TWO, rows=(), states=("VIOLATED",))
    set_right = (
        "table right_named:\n    union all:\n        from rhs\n        from rhs\n"
        + DIRECT.replace("join rhs as r", "join right_named as r")
    )
    add("set_right_multiplicity", set_right, rows=(), states=("VIOLATED",))
    earlier = "table earlier:\n    from lhs\n    inner join rhs as r:\n        from lhs\n        on lhs.id == r.id\n    select:\n        id = lhs.id\n        key = r.key\n"
    later = "query result:\n    from earlier\n    anti join rhs as r:\n        from earlier\n        on earlier.id == r.id\n    select:\n        left_id = earlier.id\n        right_key = earlier.key\n"
    add(
        "earlier_join_hidden_by_anti",
        earlier + later,
        rhs=TWO,
        rows=(),
        states=("VIOLATED", "VIOLATED"),
    )
    tied = (
        "table chosen:\n    from rhs\n    select:\n        id\n        key\n    order by:\n        key\n    limit 2\n"
        + DIRECT.replace("join rhs as r", "join chosen as r")
    )
    add(
        "ordinary_tied_subject",
        tied,
        lhs=((1, None),),
        rhs=((1, 0), (2, 0), (1, 0)),
        rows=(),
        states=("VIOLATED",),
        choices=((("FULFILLED",), ((1, 0),)), (("VIOLATED",), ())),
    )
    add(
        "refined_tied_subject",
        tied,
        lhs=((1, None),),
        rhs=((1, 0), (2, 0), (1, 0)),
        rows=((1, 0),),
        refined=True,
    )
    add("serializable", isolation="serializable")
    add("visibility_full", rhs=TWO, rows=(), states=("VIOLATED",))
    add("visibility_subset", rhs=TWO, rows=(), role="pietto_subset")
    bound = DIRECT.replace(
        "on lhs.id == r.id", "on lhs.id == r.id and lhs.key > 1 and r.key > 1"
    )
    for label, values, rows, states in (
        ("A", (1, 2), ((1, 3), (1, 3)), ("FULFILLED",)),
        ("B", (1, 1), (), ("VIOLATED",)),
        ("A_again", (1, 2), ((1, 3), (1, 3)), ("FULFILLED",)),
    ):
        add(
            "binding_" + label,
            bound,
            lhs=((1, 4), (1, 4)),
            rhs=((1, 2), (1, 3)),
            rows=rows,
            states=states,
            policy="bind_safe_literals",
            binding_values=values,
        )
    four = (
        DIRECT.replace("on lhs.id == r.id", "on lhs.id == r.id and lhs.id > 0")
        + '        flag = true\n        ratio = 0.0\n        note = "v"\n'
    )
    four_rows = ((1, None, True, 0.0, "v"), (1, None, True, 0.0, "v"))
    add("bound_four", four, rows=four_rows, policy="bind_safe_literals")
    add(
        "bound_four_refined",
        four,
        rows=four_rows,
        policy="bind_safe_literals",
        refined=True,
    )
    null_right = (
        "table null_right:\n    from rhs\n    select:\n        id = key\n        key\n"
        + DIRECT.replace("inner join rhs", "left join null_right").replace(
            "on lhs.id == r.id", "on true"
        )
    )
    add("all_null_actual_matches", null_right, rhs=TWO, rows=(), states=("VIOLATED",))
    add(
        "all_null_unmatched", null_right, rhs=(), rows=((1, None), (1, None), (2, None))
    )
    add("reserved_prefix", DIRECT.replace("left_id =", "__PIETTO_GUARD_DATA ="))
    from _pietto_phase68_slice5_cases import seven_rows

    for precision, state in (
        (39, "values"),
        (39, "empty"),
        (39, "null"),
        (65, "values"),
    ):
        expected = (
            ()
            if state == "empty"
            else ((None,) * 9,)
            if state == "null"
            else seven_rows("postgres", precision)
        )
        add(
            "seven_" + str(precision) + "_" + state,
            rows=expected,
            states=(),
            seven=(precision, state),
            allow=False,
        )
    imported = {
        "a.pietto": emission.JOIN_WITNESS_HEADER.format(target="{target}")
        + "table prod:\n    from rhs\n    select:\n        id\n        key\ntable base:\n    from lhs\n    select:\n        id\nexport:\n    table prod\n    table base\n",
        "b.pietto": 'import "a.pietto":\n    table prod as Mid\n    table base as Root\nexport:\n    table Mid\n    table Root\n',
        "main.pietto": 'import "b.pietto":\n    table Mid as Public\n    table Root as Left\nquery result:\n    from Left\n    inner join Public as r:\n        from Left\n        on Left.id == r.id\n    select:\n        left_id = Left.id\n        right_key = r.key\n',
    }
    add("imported_reexport", imported)
    add("imported_reexport_violation", imported, rhs=TWO, rows=(), states=("VIOLATED",))
    return tuple(records)


def case_preparation(directory, target, case):
    from pietto._project.project_guard_preparation import (
        prepare_guarded,
        prepare_guarded_request,
    )

    if "seven" in case["options"]:
        from _pietto_phase68_slice5_cases import seven_artifact

        precision, state = case["options"]["seven"]
        directory.mkdir(parents=True, exist_ok=True)
        artifact = seven_artifact(
            directory / "seven-source", target, precision=precision, state=state
        )
        if artifact is None:
            raise ValueError("seven-scalar fixture did not produce an artifact")
        return prepare_guarded_request(artifact.request)
    options = {
        k: v
        for k, v in case["options"].items()
        if k
        in (
            "requested",
            "copies",
            "policy",
            "scope",
            "link",
            "right_unique",
            "wide_text",
        )
    }
    body = case["body"]
    if type(body) is dict:
        body = {name: text.replace("{target}", target) for name, text in body.items()}
    return prepare_guarded(*planned(directory, target, body, **options))
