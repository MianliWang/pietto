"""Original selected-window binding retention through completion and Query Block IR."""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any

import pytest

from pietto._project.window_semantics import (
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultProjectFact,
    retained_window_computation_input,
    deduplicate_window_dependency_edges,
)
from pietto.semantic.window_input_analysis import WindowInputScope
from pietto._project.project_sql_plan_windows import (
    ProjectSQLWindowReference,
    ProjectNoJoinQualify,
)
from pietto._project.project_sql_plan_expressions import ProjectSQLReference
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _roots


SOURCES = {
    "ordinary_selected": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
""",
    "named_use": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
        w = rank() window named
        w2 = dense_rank() window named
    window named:
        order by:
            id
""",
    "selected_and_hidden": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and w <= 2
""",
    "grouped_satisfying_window": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    group by:
        id
    select:
        total = count()
        w = rank() window:
            order by:
                total
    satisfying:
        total > 0
    qualify:
        w <= 3
""",
    "argument_default_partition_order": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    let:
        alias = value
    select:
        w = lag(alias, 1, id) window:
            partition by:
                id
            order by:
                id
""",
}


def _reachable(*roots: object) -> dict[int, Any]:
    pending = list(roots)
    seen: dict[int, Any] = {}
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen[id(value)] = value
        if is_dataclass(value) and not isinstance(value, type):
            pending.extend(getattr(value, member.name) for member in fields(value))
        elif isinstance(value, Mapping):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (tuple, list, set, frozenset)):
            pending.extend(value)
    return seen


@pytest.mark.parametrize("case", tuple(SOURCES))
def test_normal_translation_retains_every_original_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    original = WindowInputScope.resolve
    observed: list[tuple[Any, Any, Any]] = []

    def observe(scope, expression, **kwargs):
        binding = original(scope, expression, **kwargs)
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        if frame.f_back.f_code.co_name == "_window_input_dependency":
            observed.append((scope, expression, binding))
        return binding

    monkeypatch.setattr(WindowInputScope, "resolve", observe)
    completed, bundle, _ = _roots(tmp_path, SOURCES[case])
    assert completed.ok, completed.diagnostics
    reachable = _reachable(completed, bundle)
    uses = [
        value
        for value in reachable.values()
        if type(value) is WindowDependencyOccurrence
    ]
    assert observed and uses
    for scope, expression, binding in observed:
        assert binding is not None
        assert reachable[id(scope)] is scope and reachable[id(binding)] is binding
        matches = [
            use
            for use in uses
            if use.computation is not None
            and use.computation.scope is scope
            and use.expression is expression
            and use.binding is binding
        ]
        assert len(matches) == 1
        computation = matches[0].computation
        assert computation is not None
        assert computation.project_schema is not None
        assert len(computation.project_targets) == len(scope.bindings)
        assert any(binding is candidate for candidate in scope.bindings)
        target = computation.project_targets[
            next(
                i for i, candidate in enumerate(scope.bindings) if candidate is binding
            )
        ]
        if case == "grouped_satisfying_window":
            assert target is computation.definition.select_items[0]
        elif matches[0].role is WindowDependencyRole.WINDOW_ARGUMENT:
            assert computation.definition.let_clause is not None
            assert target is computation.definition.let_clause.bindings[0]
        else:
            assert target is computation.project_schema.fields["id"]
    assert len(observed) == sum(use.binding is not None for use in uses)
    for use in uses:
        assert use.computation is not None
        assert use.expression is not None
        if use.role is WindowDependencyRole.RELATION_INPUT:
            assert use.binding is None
            assert (
                use.expression is use.computation.analysis.semantic_fact.expression.call
            )
        # Additional private context must not change historical summary behavior.
        summary = replace(use)
        assert summary.computation is summary.expression is summary.binding is None
        assert (
            summary == use and hash(summary) == hash(use) and repr(summary) == repr(use)
        )
        assert deduplicate_window_dependency_edges(
            (summary, use)
        ) == deduplicate_window_dependency_edges((use,))


@pytest.mark.parametrize(
    "change", ("partial", "nonmember", "wrong_member", "expression", "role", "bool")
)
def test_retained_dependency_constructor_rejects_corruption(
    tmp_path: Path, change: str
) -> None:
    roots = _roots(tmp_path, SOURCES["ordinary_selected"])
    use = next(
        value
        for value in _reachable(*roots).values()
        if type(value) is WindowDependencyOccurrence and value.binding is not None
    )
    assert use.binding is not None and use.expression is not None
    assert use.computation is not None
    context, expression, binding = use.computation, use.expression, use.binding
    changes: dict[str, Any] = {}
    if change == "partial":
        construction = (context,)
    else:
        if change == "nonmember":
            binding = replace(binding)
        elif change == "wrong_member":
            binding = context.scope.bindings[1]
        elif change == "expression":
            expression = replace(expression)
        elif change == "role":
            changes["role"] = WindowDependencyRole.WINDOW_PARTITION
        else:
            changes["global_ordinal"] = True
        construction = (context, expression, binding)
    with pytest.raises((ValueError, TypeError)):
        replace(use, _construction=construction, **changes)


@pytest.mark.parametrize(
    "change", ("owner", "analysis", "item", "partial", "lost", "reordered")
)
def test_retained_fact_context_cannot_cross_computations(
    tmp_path: Path, change: str
) -> None:
    roots = _roots(tmp_path, SOURCES["ordinary_selected"])
    fact = next(
        value
        for value in _reachable(*roots).values()
        if type(value) is WindowResultProjectFact
    )
    context = fact.dependency_occurrences[0].computation
    assert context is not None
    assert retained_window_computation_input(fact) is context
    if change in {"lost", "reordered", "item"}:
        with pytest.raises((ValueError, TypeError)):
            if change == "lost":
                replace(fact, dependency_occurrences=fact.dependency_occurrences[:-1])
            elif change == "reordered":
                replace(
                    fact,
                    dependency_occurrences=tuple(reversed(fact.dependency_occurrences)),
                )
            else:
                replace(context, item=replace(context.item))
        return
    changed = (
        None
        if change == "partial"
        else replace(context, definition=replace(context.definition))
        if change == "owner"
        else replace(context, analysis=replace(context.analysis))
    )
    occurrences = tuple(
        replace(
            use,
            _construction=None
            if changed is None
            else (changed, use.expression, use.binding),
        )
        if i == 0 or change != "partial"
        else use
        for i, use in enumerate(fact.dependency_occurrences)
    )
    candidate = replace(fact, dependency_occurrences=occurrences)
    assert retained_window_computation_input(candidate) is None
    assert retained_window_computation_input(fact) is context


HIDDEN_SOURCES = {
    "hidden_bare": """shape Row:
    id: Int not null
    other: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        constant = 1
    qualify:
        row_number() window:
            order by:
                id
        <= 3
""",
    "hidden_qualified": """shape Row:
    id: Int not null
    other: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        constant = 1
    qualify:
        row_number() window:
            order by:
                rows.id
        <= 3
""",
    "hidden_navigation": """shape Row:
    id: Int not null
    other: Int not null
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        constant = 1
    qualify:
        lag(rows.id, 1, rows.other) window:
            partition by:
                rows.other
            order by:
                rows.id
        > 0
""",
}


@pytest.mark.parametrize("case", tuple(HIDDEN_SOURCES))
def test_hidden_preparation_retains_new_lookups_and_project_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from pietto._project.project_final_outputs import (
        ProjectNoJoinHiddenWindowComputation,
    )

    original = WindowInputScope.resolve
    observed: list[tuple[Any, Any, Any]] = []

    def observe(scope, expression, **kwargs):
        binding = original(scope, expression, **kwargs)
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        caller = frame.f_back
        if caller.f_code.co_name == "prepare_inputs" and caller.f_globals[
            "__name__"
        ].endswith("project_final_outputs"):
            observed.append((scope, expression, binding))
        return binding

    monkeypatch.setattr(WindowInputScope, "resolve", observe)
    roots = _roots(tmp_path, HIDDEN_SOURCES[case])
    assert roots[0].ok, roots[0].diagnostics
    hidden = [
        v
        for v in _reachable(*roots).values()
        if type(v) is ProjectNoJoinHiddenWindowComputation
    ]
    assert len(hidden) == 1
    computation = hidden[0]
    assert computation.input_context is not None and computation.input_uses is not None
    uses = computation.input_uses
    field_uses = [
        use for use in uses if use.role is not WindowDependencyRole.RELATION_INPUT
    ]
    assert len(field_uses) == len(observed) == (4 if case == "hidden_navigation" else 1)
    for use, (scope, expression, binding) in zip(field_uses, observed, strict=True):
        assert use.context is computation.input_context
        assert (
            scope is computation.scope
            and use.expression is expression
            and use.binding is binding
        )
        assert binding is not None
        assert (
            use.target
            is computation.input_context.input_schema.fields[binding.target_name]
        )
        assert any(binding is member for member in scope.bindings)
        assert use.hidden is computation.expression
    assert tuple(use.global_ordinal for use in uses) == tuple(range(len(uses)))
    if case == "hidden_navigation":
        assert tuple(use.role for use in uses) == (
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_DEFAULT,
            WindowDependencyRole.WINDOW_PARTITION,
            WindowDependencyRole.WINDOW_ORDER,
        )
    else:
        assert (
            uses[0].role is WindowDependencyRole.RELATION_INPUT
            and uses[0].binding is None
        )
    assert replace(computation).input_context is None
    assert replace(computation).input_uses is None


def _planned(path: Path, source: str):
    from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), plan
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    assert view.plan is plan
    return roots, plan, checked, view


@pytest.mark.parametrize("case", tuple(SOURCES) + tuple(HIDDEN_SOURCES))
def test_real_predecessors_hidden_and_mixed_projection_pipeline(
    tmp_path: Path, case: str
) -> None:
    from pietto._project import project_sql_plan_windows as windows

    _, plan, _, view = _planned(tmp_path, {**SOURCES, **HIDDEN_SOURCES}[case])
    assert view.windows and view.windows is plan.windows
    for value in view.windows:
        assert view.window(value.ref) is value
        policy = view.policy_for_window(value.ref)
        assert (
            policy.specification
            is windows.analysis(value.source).validated_specification
        )
        assert policy.named_use is windows.analysis(value.source).resolved_named_use
        assert tuple(use.ref for use in view.inputs_for_window(value.ref)) == value.uses
        assert (
            tuple(argument.ref for argument in view.arguments_for_window(value.ref))
            == value.arguments
        )
        assert view.window_requirements(value.ref)
        block = next(block for block in view.blocks if block.ref is value.block)
        assert value.inputs == block.inputs
        assert all(
            use.input in block.inputs
            for use in view.inputs_for_window(value.ref)
            if use.input is not None
        )
    from pietto.ast_nodes import TableDef, QueryDef

    assert isinstance(plan.scope.selected_owner.definition, (TableDef, QueryDef))
    assert len(view.exports) == len(plan.scope.selected_owner.definition.select_items)
    if case.startswith("hidden_"):
        assert len(view.exports) == 1 and view.exports[0].identity.name == "constant"
        assert all(value.selected is None for value in view.windows)
        assert not view.window_projections
    if "hidden" in case or "satisfying" in case:
        assert view.qualify_sites
        assert [block.kind.value for block in view.blocks][-3:] == [
            "window",
            "qualify",
            "projection",
        ]


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
        body = f"{kind} result:\n    from rows\n    select:\n        id\n        w = {call} window composed\n    window composed = base\n    window base:\n        order by:\n            id desc\n"
        if frame is not None:
            body += f"        {frame}\n"
    else:
        body = f"{kind} result:\n    from rows\n    select:\n        id\n        w = {call} window:\n            order by:\n                id desc\n"
        if frame is not None:
            body += f"            {frame}\n"
    return prefix + body


@pytest.mark.parametrize("call,frame", FAMILIES)
@pytest.mark.parametrize("named", (False, True))
@pytest.mark.parametrize("kind,backend", (("query", "postgres"), ("table", "mysql")))
def test_all_admitted_families_named_and_inline(
    tmp_path: Path, call: str, frame: str | None, named: bool, kind: str, backend: str
) -> None:
    from pietto._project import project_sql_plan_windows as windows

    _, plan, _, view = _planned(
        tmp_path, _family_source(call, frame, named, kind, backend)
    )
    (value,) = plan.windows
    assert value.function.name == call.split("(")[0]
    assert (view.policy_for_window(value.ref).named_use is not None) is named
    assert len(value.arguments) == len(value.effective.call.arguments)
    assert value.value_type is windows.result_type(value.source)
    for use in view.inputs_for_window(value.ref):
        if use.binding is not None:
            assert use.value_type == use.binding.value_type
    assert view.policy_for_window(
        value.ref
    ).specification.resolved.frame.applicability.value == (
        "not_applicable" if frame is None else "applicable"
    )


COMPOSED_SOURCES = {
    "joined_let_where_window": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
source other: Row is postgres.table("other")
query result:
    from rows
    left join other as r:
        from rows
        on rows.id == r.id
    let:
        alias = r.value
    where rows.id > 0
    select:
        id = rows.id
        w = lag(alias, 1, 0) window:
            order by:
                rows.id
    qualify:
        w > 0
""",
    "joined_hidden_constant": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
source other: Row is postgres.table("other")
query result:
    from rows
    left join other as r:
        from rows
        on rows.id == r.id
    select:
        constant = 1
    qualify:
        row_number() window:
            order by:
                rows.id
        <= 3
""",
    "named_windowed_consumer": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
table upstream:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
query result:
    from upstream
    where w > 0
    select:
        id
        w
""",
    "named_global_then_window": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
table upstream:
    from rows
    select:
        total = count()
query result:
    from upstream
    select:
        total
        w = row_number() window:
            order by:
                total
""",
}


@pytest.mark.parametrize("case", tuple(COMPOSED_SOURCES))
def test_joined_and_named_predecessors_complete_through_inspection(
    tmp_path: Path, case: str
) -> None:
    _, plan, _, view = _planned(tmp_path, COMPOSED_SOURCES[case])
    assert plan.windows
    assert all(view.window(value.ref) is value for value in plan.windows)
    if case.startswith("joined"):
        assert plan.joins
    else:
        assert len(plan.bindings.definitions) > 2


@pytest.mark.parametrize(
    "body",
    (
        "    select:\n        id\n        a = w\n        b = w\n",
        "    let:\n        alias = w\n    where alias > 0\n    select:\n        w = lag(alias, 1, 0) window:\n            order by:\n                id\n",
        "    group by:\n        id\n    select:\n        total = count()\n    satisfying:\n        total > 0\n",
        "    select:\n        total = sum(w)\n",
    ),
)
def test_windowed_producer_rebound_consumers_keep_immediate_exports(
    tmp_path: Path, body: str
) -> None:
    source = (
        SOURCES["selected_and_hidden"].replace("query result:", "table upstream:")
        + "query result:\n    from upstream\n"
        + body
    )
    _, plan, _, view = _planned(tmp_path, source)
    upstream = next(
        definition
        for definition in plan.bindings.definitions
        if definition.entry.owner.definition.name == "upstream"
    )
    consumer = plan.bindings.definitions[-1]
    use = next(use for use in plan.input_uses if use.consumer is consumer.ref)
    assert use.producer is upstream.ref
    assert tuple(port.producer_port for port in use.ports) == tuple(
        port.ref for port in upstream.exports
    )
    assert all(window.definition is upstream.ref for window in view.windows[:2])


@pytest.mark.parametrize(
    "kind", ("inner", "left", "right", "full", "semi", "anti", "cross")
)
def test_all_join_kinds_feed_window_membership(tmp_path: Path, kind: str) -> None:
    prefix = SOURCES["ordinary_selected"].split("query result:")[0]
    condition = "" if kind == "cross" else "        on rows.id == r.id\n"
    source = (
        prefix
        + f"""query result:
    from rows
    {kind} join rows as r:
        from rows
{condition}    select:
        w = row_number() window:
            order by:
                rows.id
    qualify:
        w <= 3
"""
    )
    roots, plan, _, view = _planned(tmp_path, source)
    assert plan.joins and len(plan.windows) == 1
    assert plan.diagnostics is roots[0].diagnostics
    assert view.inputs_for_window(plan.windows[0].ref)[0].input is None
    assert plan.windows[0].inputs


@pytest.fixture(scope="module")
def window_plans(tmp_path_factory: pytest.TempPathFactory):
    source = (
        SOURCES["selected_and_hidden"]
        .replace(
            "w = row_number() window:\n            order by:\n                id",
            "w = lag(value, 1, id) window declared",
        )
        .replace(
            "    qualify:",
            "    window declared:\n        order by:\n            id\n    qualify:",
        )
    )
    return tuple(
        _planned(tmp_path_factory.mktemp("window-plan"), source) for _ in range(2)
    )


@pytest.mark.parametrize(
    "inventory",
    (
        "windows",
        "window_uses",
        "window_arguments",
        "window_policies",
        "window_projections",
    ),
)
@pytest.mark.parametrize("change", ("empty", "duplicate", "reverse", "foreign"))
def test_window_inventories_cannot_disappear_or_change_identity(
    window_plans, inventory: str, change: str
) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    (roots, plan, checked, _), (_, foreign, _, _) = window_plans
    original = getattr(plan, inventory)
    assert original
    changed = (
        ()
        if change == "empty"
        else (*original, original[0])
        if change == "duplicate"
        else getattr(foreign, inventory)
        if change == "foreign"
        else tuple(reversed(original))
        if len(original) > 1
        else (*original, original[0])
    )
    candidate = _graft(plan, **{inventory: changed})
    verified = verify_project_sql_plan(candidate, *roots)
    assert not verified.verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(_graft(checked, plan=candidate))


@pytest.mark.parametrize(
    "field",
    (
        "position",
        "source",
        "context",
        "inputs",
        "result",
        "value_type",
        "selected",
        "policy",
    ),
)
def test_computation_fields_require_original_context(window_plans, field: str) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    (roots, plan, _, _), (_, foreign, _, _) = window_plans
    value = plan.windows[0]
    replacements = {
        "position": True,
        "source": foreign.windows[0].source,
        "context": foreign.windows[0].context,
        "inputs": (),
        "result": plan.windows[1].result,
        "value_type": replace(value.value_type),
        "selected": None,
        "policy": plan.windows[1].policy,
    }
    changed = _graft(value, **{field: replacements[field]})
    assert not verify_project_sql_plan(
        _graft(plan, windows=(changed, *plan.windows[1:])), *roots
    ).verified


@pytest.mark.parametrize(
    "field",
    (
        "position",
        "role_position",
        "role",
        "expression",
        "input",
        "binding",
        "value_type",
    ),
)
def test_window_use_fields_and_bindings_are_exact(window_plans, field: str) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    (roots, plan, _, _), (_, foreign, _, _) = window_plans
    use = next(use for use in plan.window_uses if use.binding is not None)
    changes = {
        "position": True,
        "role_position": True,
        "role": WindowDependencyRole.WINDOW_DEFAULT,
        "expression": replace(use.expression),
        "input": plan.windows[0].result,
        "binding": foreign.window_uses[0].binding,
        "value_type": None,
    }
    candidate = _graft(
        plan,
        window_uses=tuple(
            _graft(use, **{field: changes[field]}) if value is use else value
            for value in plan.window_uses
        ),
    )
    assert not verify_project_sql_plan(candidate, *roots).verified


@pytest.mark.parametrize(
    "field",
    (
        "specification",
        "modifiers",
        "namespace",
        "ir_operator",
        "ir_policy",
        "ir_effect",
        "navigation",
    ),
)
def test_window_policy_grafts_are_rejected(window_plans, field: str) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    (roots, plan, _, _), (_, foreign, _, _) = window_plans
    policy = plan.window_policies[0]
    changed = getattr(foreign.window_policies[0], field)
    assert changed is not getattr(policy, field)
    candidate = _graft(
        plan,
        window_policies=(_graft(policy, **{field: changed}), *plan.window_policies[1:]),
    )
    assert not verify_project_sql_plan(candidate, *roots).verified


@pytest.mark.parametrize(
    "change",
    (
        "window_demands",
        "window_origins",
        "hidden_export",
        "filter_loss",
        "argument_role",
        "projection",
    ),
)
def test_window_requirements_and_stage_crossings_are_mandatory(
    window_plans, change: str
) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project import project_sql_plan_windows as windows
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    (roots, plan, _, _), _ = window_plans
    if change == "window_demands":
        candidate = _graft(
            plan,
            demands=tuple(
                demand
                for demand in plan.demands
                if not isinstance(demand, windows.ProjectSQLWindowDemand)
            ),
        )
    elif change == "window_origins":
        candidate = _graft(
            plan,
            origins=tuple(
                origin
                for origin in plan.origins
                if not origin.role.value.startswith("window")
            ),
        )
    elif change == "hidden_export":
        final = plan.blocks[-1]
        candidate = _graft(
            plan,
            blocks=(
                *plan.blocks[:-1],
                _graft(final, exports=(*final.exports, plan.windows[1].result)),
            ),
        )
    elif change == "filter_loss":
        candidate = _graft(plan, filters=())
    elif change == "argument_role":
        argument = plan.window_arguments[1]
        candidate = _graft(
            plan,
            window_arguments=tuple(
                _graft(argument, role=windows.ProjectSQLWindowArgumentRole.DEFAULT)
                if value is argument
                else value
                for value in plan.window_arguments
            ),
        )
    else:
        projection = plan.window_projections[0]
        candidate = _graft(
            plan, window_projections=(_graft(projection, input=plan.windows[1].result),)
        )
    assert not verify_project_sql_plan(candidate, *roots).verified


def test_named_template_sharing_keeps_use_local_inputs_and_unused_templates(
    tmp_path: Path,
) -> None:
    prefix = SOURCES["ordinary_selected"].split("query result:")[0]
    _, plan, _, view = _planned(
        tmp_path,
        prefix
        + """query result:
    from rows
    select:
        a = rank() window base
        b = dense_rank() window copied
        c = row_number() window base:
            partition by:
                id
    window copied = base
    window base:
        order by:
            id
    window unused:
        order by:
            value
        rows between unbounded preceding and current row
""",
    )
    assert len(plan.windows) == 3
    first, second, third = plan.windows
    assert first.effective.spec.order_by[0] is second.effective.spec.order_by[0]
    assert first.context is not second.context
    first_use = view.inputs_for_window(first.ref)[-1]
    second_use = view.inputs_for_window(second.ref)[-1]
    assert first_use.expression is second_use.expression
    assert (
        first_use.source is not second_use.source
        and first_use.binding is not second_use.binding
    )
    assert len(view.inputs_for_window(third.ref)) == 3
    assert len(view.window_policies) == 3
    for policy in view.window_policies:
        assert policy.named_use is not None
        assert policy.named_use.composed.target_template.declaration.name != "unused"


@pytest.mark.parametrize(
    "call", ("lag(value, 1, null)", "lag(null, 0, 1)", "lead(value)", "ntile(1)")
)
def test_specialized_literals_defaults_and_omissions_keep_their_own_types(
    tmp_path: Path, call: str
) -> None:
    from pietto.ast_nodes import LiteralExpr

    _, plan, _, view = _planned(
        tmp_path, _family_source(call, None, False, "query", "postgres")
    )
    (value,) = view.windows
    for argument in view.arguments_for_window(value.ref):
        if isinstance(argument.expression, LiteralExpr):
            assert argument.use is None
    assert value.inputs
    assert len(plan.exports) == 2


def test_repeated_selected_references_reuse_the_established_window_value(
    tmp_path: Path,
) -> None:
    source = SOURCES["ordinary_selected"] + "    qualify:\n        w > 0 and w <= 3\n"
    _, plan, _, view = _planned(tmp_path, source)
    assert len(plan.windows) == 1
    (site,) = view.qualify_sites
    references = [
        value
        for value in view.expressions_for_site(site.ref)
        if isinstance(value, ProjectSQLWindowReference)
    ]
    assert len(references) == 2 and references[0].port is references[1].port
    assert len(view.uses_of(references[0].port)) == 2


@pytest.mark.parametrize(
    "body,lookups,prepared",
    (
        (
            "row_number(1) window:\n            order by:\n                id\n        <= 3",
            0,
            False,
        ),
        (
            "row_number() window:\n            order by:\n                missing\n        <= 3",
            1,
            True,
        ),
        (
            "row_number() window:\n            partition by:\n                id + 1\n            order by:\n                id\n        <= 3",
            1,
            True,
        ),
    ),
)
def test_hidden_early_rejection_and_unresolved_attempts_preserve_kernel_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    lookups: int,
    prepared: bool,
) -> None:
    from pietto._project import project_final_outputs as final_outputs

    prefix = HIDDEN_SOURCES["hidden_bare"].split("    qualify:")[0]
    source = prefix + "    qualify:\n        " + body + "\n"
    original_resolve = WindowInputScope.resolve
    calls = []

    def observe(scope, expression, **kwargs):
        frame = inspect.currentframe()
        assert frame is not None and frame.f_back is not None
        binding = original_resolve(scope, expression, **kwargs)
        if frame.f_back.f_code.co_name == "prepare_inputs":
            calls.append((scope, expression, binding))
        return binding

    monkeypatch.setattr(WindowInputScope, "resolve", observe)
    roots = _roots(tmp_path / "prepared", source)
    assert not roots[0].ok
    attempts = [
        value
        for value in _reachable(*roots).values()
        if isinstance(value, final_outputs.ProjectNoJoinHiddenWindowComputation)
    ]
    assert len(attempts) == 1 and len(calls) == lookups
    assert (attempts[0].input_uses is not None) is prepared
    original_analyze = final_outputs.analyze_window_computation

    def without_preparation(**kwargs):
        kwargs.pop("prepare_inputs", None)
        return original_analyze(**kwargs)

    monkeypatch.setattr(
        final_outputs, "analyze_window_computation", without_preparation
    )
    baseline = _roots(tmp_path / "original-kernel", source)
    assert baseline[0].ok is roots[0].ok
    assert baseline[0].diagnostics == roots[0].diagnostics


@pytest.mark.parametrize("case", ("selected_and_hidden", "grouped_satisfying_window"))
def test_plan_verification_and_inspection_do_not_rebuild_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from pietto._project import project_sql_plan as planning
    from pietto._project import project_sql_plan_windows as windows
    from pietto._project import project_sql_plan_expressions as row
    from pietto._project import project_final_outputs as final_outputs
    from pietto._project import module_semantic_fact_preservation as preservation
    from pietto.semantic import (
        window_analysis,
        window_input_analysis,
        window_semantics,
        expressions,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    roots = _roots(tmp_path, SOURCES[case])

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Downstream window work must consume original retained products"
        )

    monkeypatch.setattr(WindowInputScope, "resolve", forbidden)
    for module, names in (
        (
            final_outputs,
            (
                "_hidden_no_join_window",
                "analyze_window_computation",
                "build_window_input_scope",
                "_window_project_targets",
            ),
        ),
        (
            preservation,
            (
                "_window_project_targets",
                "analyze_window_expression",
                "build_window_input_scope",
            ),
        ),
        (window_analysis, ("analyze_window_expression", "analyze_window_computation")),
        (window_input_analysis, ("build_window_input_scope",)),
        (expressions, ("infer_row_expression",)),
        (
            window_semantics,
            (
                "resolve_named_window_namespace",
                "compose_named_window_use",
                "resolve_composed_named_window_use",
            ),
        ),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    plan = planning.build_project_sql_plan(*roots)
    assert isinstance(plan, planning.ProjectSQLPlan)
    monkeypatch.setattr(planning, "build_project_sql_plan", forbidden)
    monkeypatch.setattr(planning, "build_project_sql_bindings", forbidden)
    monkeypatch.setattr(row, "scalar_nodes", forbidden)
    monkeypatch.setattr(row, "scalar_children", forbidden)
    for cls in (
        windows.ProjectSQLWindow,
        windows.ProjectSQLWindowUse,
        windows.ProjectSQLWindowArgument,
        windows.ProjectSQLWindowPolicy,
        windows.ProjectSQLWindowProjection,
        windows.ProjectSQLWindowReference,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    assert inspect_project_sql_plan(checked).windows is plan.windows


@pytest.mark.parametrize("grouped", (False, True))
def test_hidden_inputs_and_outer_qualify_share_original_project_target_bridge(
    tmp_path: Path, grouped: bool
) -> None:
    prefix = SOURCES["ordinary_selected"].split("query result:")[0]
    body = (
        """    let:
        alias = value
    select:
        constant = 1
    qualify:
        lag(alias, 1, 0) window:
            order by:
                id
        > 0 and id > 0
"""
        if not grouped
        else """    group by:
        id
    select:
        key = id
        total = count()
    satisfying:
        total > 0
    qualify:
        lag(total, 1, 0) window:
            partition by:
                key
            order by:
                total
        > 0 and key > 0 and total > 0
"""
    )
    _, plan, _, view = _planned(
        tmp_path, prefix + "query result:\n    from rows\n" + body
    )
    assert len(plan.windows) == 1 and plan.windows[0].selected is None
    assert view.qualify_sites
    assert len(view.inputs_for_window(plan.windows[0].ref)) == (3 if grouped else 2)
    context = plan.windows[0].context
    assert isinstance(view.qualify_sites[0].evidence, ProjectNoJoinQualify)
    assert view.qualify_sites[0].evidence.input_context is context
    assert all(
        use.input is not None for use in view.inputs_for_window(plan.windows[0].ref)
    )


def test_repeated_hidden_computations_keep_shared_scope_but_separate_results(
    tmp_path: Path,
) -> None:
    source = HIDDEN_SOURCES["hidden_bare"].replace(
        "        <= 3\n",
        """        <= 3 and row_number() window:
            order by:
                id
        > 0
""",
    )
    _, plan, _, view = _planned(tmp_path, source)
    first, second = plan.windows
    assert first.context is second.context
    assert first.source is not second.source and first.result is not second.result
    assert first.inputs == second.inputs
    first_use, second_use = (
        view.inputs_for_window(first.ref)[-1],
        view.inputs_for_window(second.ref)[-1],
    )
    assert first_use.binding is second_use.binding
    assert first_use.source is not second_use.source
    assert len(plan.exports) == 1


@pytest.mark.parametrize(
    "mutation",
    (
        "missing",
        "partial",
        "wrong_target",
        "foreign_scope",
        "lost_use",
        "bool",
        "derived",
    ),
)
def test_old_verified_ir_does_not_certify_new_hidden_binding_ledger(
    tmp_path: Path, mutation: str
) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project import project_sql_plan as planning
    from pietto._project import project_sql_plan_windows as windows
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    roots, plan, checked, _ = _planned(tmp_path, HIDDEN_SOURCES["hidden_navigation"])
    source = plan.windows[0].source
    assert isinstance(source, windows.ProjectNoJoinHiddenWindowComputation)
    original_uses, original_context = source.input_uses, source.input_context
    assert original_uses and original_context is not None
    changed = (
        None
        if mutation == "missing"
        else ()
        if mutation == "partial"
        else original_uses[:-1]
        if mutation == "lost_use"
        else original_uses
    )
    if mutation == "wrong_target":
        changed = (
            _graft(original_uses[0], target=original_context.targets[1]),
            *original_uses[1:],
        )
    elif mutation == "bool":
        changed = (_graft(original_uses[0], global_ordinal=True), *original_uses[1:])
    context = (
        _graft(original_context, scope=replace(original_context.scope))
        if mutation == "foreign_scope"
        else None
        if mutation == "derived"
        else original_context
    )
    try:
        object.__setattr__(source, "input_uses", changed)
        object.__setattr__(source, "input_context", context)
        assert roots[1].verification.verified
        assert isinstance(
            planning.build_project_sql_plan(*roots), planning.ProjectSQLPlanUnavailable
        )
        assert not verify_project_sql_plan(plan, *roots).verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(checked)
    finally:
        object.__setattr__(source, "input_uses", original_uses)
        object.__setattr__(source, "input_context", original_context)
    assert verify_project_sql_plan(plan, *roots).verified


def test_imported_reexported_windowed_producer_preserves_logical_reuse(
    tmp_path: Path,
) -> None:
    producer = SOURCES["selected_and_hidden"].replace("query result:", "table first:")
    (tmp_path / "a.pietto").write_text(producer + "export:\n    table first\n")
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    _, plan, _, view = _planned(
        tmp_path,
        """import "b.pietto":
    table Public as Alias
query result:
    from Alias
    let:
        value = w
    where value > 0
    select:
        first = value
        second = value
""",
    )
    assert len(plan.windows) == 2
    owner = plan.scope.selected_owner
    use = next(use for use in view.input_uses if use.dependency.consumer is owner)
    assert use.binding.imported_binding is not None
    assert (
        use.origin_path.target_occurrence.identity
        is plan.bindings.definitions[-2].entry.owner.identity
    )
    refs = [
        expression
        for expression in view.expressions
        if isinstance(expression, ProjectSQLReference)
        and expression.site.owner is owner
        and expression.site.role.value == "select"
    ]
    assert len(refs) == 2 and refs[0].port is refs[1].port
    assert [export.identity.name for export in view.exports] == ["first", "second"]


def test_qualify_does_not_discharge_original_single_match_obligation(
    tmp_path: Path,
) -> None:
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _product,
        _source,
        _requests,
    )

    source = _source(
        "inner",
        "lhs.id < r.id",
        tail="""    select:
        w = row_number() window:
            order by:
                lhs.id
    qualify:
        w <= 1
""",
    )
    roots, plan, view = _product(tmp_path, source, _requests)
    assert plan.windows
    (obligation,) = view.single_matches
    assert obligation.assessment is roots[0].single_matches.entries[0]
    assert obligation.downstream_enforcement_required
    assert (
        obligation.diagnostic is not None and obligation.diagnostic in plan.diagnostics
    )


@pytest.mark.parametrize("change", ("distinct", "order", "limit", "scalar_call"))
def test_future_stages_and_general_calls_remain_unavailable(
    tmp_path: Path, change: str
) -> None:
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanUnavailable,
        build_project_sql_plan,
    )

    source = HIDDEN_SOURCES["hidden_bare"]
    if change == "distinct":
        source = source.replace("    select:", "    select distinct:")
    elif change == "order":
        source += "    order by:\n        id\n"
    elif change == "limit":
        source += "    limit 1\n"
    else:
        source = SOURCES["ordinary_selected"] + '    qualify:\n        len("x") > w\n'
    roots = _roots(tmp_path, source)
    assert roots[0].ok, roots[0].diagnostics
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)


def test_where_false_and_repeated_order_uses_keep_computation_and_membership(
    tmp_path: Path,
) -> None:
    source = (
        SOURCES["ordinary_selected"]
        .replace("    select:", "    where false\n    select:")
        .replace(
            "                id\n", "                id asc\n                id desc\n"
        )
    )
    _, plan, _, view = _planned(tmp_path, source)
    assert [block.kind.value for block in plan.blocks] == [
        "where",
        "window",
        "projection",
    ]
    (value,) = plan.windows
    uses = view.inputs_for_window(value.ref)
    assert len(uses) == 3
    assert uses[1].binding is uses[2].binding and uses[1].source is not uses[2].source
    assert uses[1].input is uses[2].input
    assert [
        order.effective_direction for order in view.policy_for_window(value.ref).orders
    ] == ["asc", "desc"]
    assert value.inputs


def test_repeated_windowed_producer_uses_keep_one_definition_and_two_inputs(
    tmp_path: Path,
) -> None:
    producer = SOURCES["selected_and_hidden"].replace(
        "query result:", "table upstream:"
    )
    _, plan, _, view = _planned(
        tmp_path,
        producer
        + """query result:
    from upstream
    left join upstream as r:
        from upstream
        on upstream.id == r.id
    select:
        first = upstream.w
        second = r.w
""",
    )
    producer_definition = next(
        definition
        for definition in plan.bindings.definitions
        if definition.entry.owner.definition.name == "upstream"
    )
    uses = [use for use in view.input_uses if use.producer is producer_definition.ref]
    assert len(uses) == 2 and uses[0].ref is not uses[1].ref
    assert (
        len(
            [
                window
                for window in view.windows
                if window.definition is producer_definition.ref
            ]
        )
        == 2
    )
    assert [field.identity.name for field in view.exports] == ["first", "second"]


@pytest.mark.parametrize("field", ("argument_position", "bucket_count"))
def test_structural_window_ordinals_and_counts_do_not_accept_bool(
    tmp_path: Path, field: str
) -> None:
    from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
        _graft,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan

    roots, plan, _, _ = _planned(
        tmp_path, _family_source("ntile(1)", None, False, "query", "postgres")
    )
    if field == "argument_position":
        candidate = _graft(
            plan, window_arguments=(_graft(plan.window_arguments[0], position=False),)
        )
    else:
        candidate = _graft(
            plan, window_policies=(_graft(plan.window_policies[0], bucket_count=True),)
        )
    assert not verify_project_sql_plan(candidate, *roots).verified


@pytest.mark.parametrize("case", tuple(HIDDEN_SOURCES))
def test_new_hidden_preparation_preserves_original_positive_kernel_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from pietto._project import project_final_outputs as final_outputs
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanUnavailable,
        build_project_sql_plan,
    )

    roots = _roots(tmp_path / "prepared", HIDDEN_SOURCES[case])
    prepared = next(
        value
        for value in _reachable(*roots).values()
        if isinstance(value, final_outputs.ProjectNoJoinHiddenWindowComputation)
    )
    original = final_outputs.analyze_window_computation

    def without_preparation(**kwargs):
        kwargs.pop("prepare_inputs", None)
        return original(**kwargs)

    monkeypatch.setattr(
        final_outputs, "analyze_window_computation", without_preparation
    )
    old_roots = _roots(tmp_path / "kernel-only", HIDDEN_SOURCES[case])
    old = next(
        value
        for value in _reachable(*old_roots).values()
        if isinstance(value, final_outputs.ProjectNoJoinHiddenWindowComputation)
    )
    assert old_roots[0].ok and roots[0].ok
    assert old_roots[0].diagnostics == roots[0].diagnostics
    assert old.analysis == prepared.analysis
    assert old.value_types == prepared.value_types
    assert old.input_uses is None and prepared.input_uses is not None
    assert isinstance(build_project_sql_plan(*old_roots), ProjectSQLPlanUnavailable)


REJECTED_SOURCES = {
    "global_same_body": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        total = count()
        w = row_number() window:
            order by:
                total
""",
    "ambiguous_qualify": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
        id = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and id > 0
""",
    "no_window_qualify": """shape Row:
    id: Int not null
    value: Int nullable
    flag: Bool nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        id
    qualify:
        id > 0
""",
}


@pytest.mark.parametrize("case", tuple(REJECTED_SOURCES))
def test_existing_semantic_window_rejections_still_block_planning(
    tmp_path: Path, case: str
) -> None:
    from pietto._project.project_sql_plan import (
        ProjectSQLPlanUnavailable,
        build_project_sql_plan,
    )

    roots = _roots(tmp_path, REJECTED_SOURCES[case])
    assert not roots[0].ok
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlanUnavailable)
    assert plan.diagnostics is roots[0].diagnostics
    assert any(
        blocker.kind.value == "semantic_result_unsuccessful"
        for blocker in plan.blockers
    )


@pytest.mark.parametrize(
    "change",
    ("qualify_status", "qualify_aggregate", "input_schema", "dependency_result_role"),
)
def test_reviewed_window_and_qualify_authority_closure(
    tmp_path: Path, change: str
) -> None:
    from pietto._project import project_sql_plan as planning
    from pietto._project import project_sql_plan_windows as windows
    from pietto._project.model import ProjectRowResultRole
    from pietto._project.module_semantic_fact_preservation import (
        ProjectModuleCandidateBucketStatus,
    )
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan

    roots, plan, checked, view = _planned(
        tmp_path / "primary", SOURCES["grouped_satisfying_window"]
    )
    if change == "qualify_status":
        target, field, changed = (
            view.qualify_sites[0].references[0],
            "status",
            ProjectModuleCandidateBucketStatus.AMBIGUOUS,
        )
    elif change == "qualify_aggregate":
        _, _, _, foreign = _planned(
            tmp_path / "foreign", SOURCES["grouped_satisfying_window"]
        )
        target, field, changed = (
            view.qualify_sites[0],
            "aggregate",
            foreign.qualify_sites[0].aggregate,
        )
    elif change == "input_schema":
        context = plan.windows[0].context
        assert (
            isinstance(context, windows.WindowComputationInput)
            and context.project_schema is not None
        )
        target, field, changed = (
            context,
            "project_schema",
            replace(context.project_schema),
        )
    else:
        target, field, changed = (
            plan.window_uses[-1].source,
            "target_result_role",
            ProjectRowResultRole.GROUP_KEY,
        )
    previous = getattr(target, field)
    try:
        object.__setattr__(target, field, changed)
        assert not verify_project_sql_plan(plan, *roots).verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(checked)
        if change != "qualify_aggregate":
            assert isinstance(
                planning.build_project_sql_plan(*roots),
                planning.ProjectSQLPlanUnavailable,
            )
    finally:
        object.__setattr__(target, field, previous)
    assert verify_project_sql_plan(plan, *roots).verified
