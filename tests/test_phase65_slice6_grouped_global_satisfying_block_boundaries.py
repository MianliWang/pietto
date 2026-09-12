"""Real aggregate boundaries and exact determinant/output evidence."""

from pathlib import Path

import pytest

from pietto._project import project_query_block_ir as ir
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir,
)
from pietto._project.project_grain import ProjectGrainBasisState
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
)
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _graft
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _roots
from pietto._project.project_sql_plan import build_project_sql_plan, ProjectSQLPlan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project import project_sql_plan_aggregation as aggregation


def _plan_product(path: Path, source: str):
    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), tuple(b.kind for b in plan.blockers)
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    return roots, plan, inspect_project_sql_plan(checked)


def _ordinary(body: str, *, family="postgres", kind="query"):
    return f"""shape Row:
    id: Int not null
    value: Int nullable
source rows: Row is {family}.table("rows")
{kind} result:
    from rows
{body}"""


@pytest.mark.parametrize("grouped", (False, True))
@pytest.mark.parametrize("family,kind", (("postgres", "query"), ("mysql", "table")))
@pytest.mark.parametrize(
    "call,result_type,nullable",
    (
        ("count()", "Int", False),
        ("count(value)", "Int", False),
        ("count_distinct(value)", "Int", False),
        ("sum(value)", "Int", True),
        ("avg(value)", "Float", True),
        ("min(value)", "Int", True),
        ("max(value)", "Int", True),
    ),
)
def test_plan_ordinary_aggregate_forms_preserve_original_types(
    tmp_path: Path, grouped, family, kind, call, result_type, nullable
):
    group = "    group by:\n        id\n" if grouped else ""
    roots, plan, view = _plan_product(
        tmp_path,
        _ordinary(
            group + f"    select:\n        total = {call}\n", family=family, kind=kind
        ),
    )
    (stage,) = view.aggregations
    (value,) = view.aggregates
    assert value.value_type is value.source.result_value_type
    assert value.value_type.resolved_type.name == result_type
    assert (value.value_type.nullability.value == "nullable") is nullable
    assert len(view.arguments_for_aggregate(value.ref)) == (
        0 if call == "count()" else 1
    )
    assert len(stage.keys) == int(grouped)
    assert tuple(p.identity.name for p in view.exports) == ("total",)
    assert stage.empty_input is (
        aggregation.ProjectSQLAggregateEmptyInput.NO_GROUPS
        if grouped
        else aggregation.ProjectSQLAggregateEmptyInput.ONE_GLOBAL_ROW
    )
    assert len(view.aggregate_projections) == 1
    assert view.aggregate_requirements(stage.ref)
    assert plan.diagnostics is roots[0].diagnostics


def test_plan_joined_hidden_group_has_private_key_port(tmp_path: Path):
    _, plan, view = _plan_product(tmp_path, _group_source())
    (stage,) = view.aggregations
    (key,) = view.group_keys
    assert key.result in stage.results and key.result not in tuple(
        p.ref for p in view.exports
    )
    assert stage.authority.keys[0] is key.source
    assert len(view.aggregate_risks) == len(stage.authority.risks) > 0
    assert [b.kind.value for b in plan.blocks] == ["aggregate", "projection"]


def test_plan_let_where_satisfying_references_reuse_results(tmp_path: Path):
    source = _ordinary("""    let:
        key = id
        amount = value + 1
    where false
    group by:
        key
    select:
        total = sum(amount)
    satisfying:
        total > 0 and sum(amount) > 1 and total < 10
""")
    _, plan, view = _plan_product(tmp_path, source)
    assert [b.kind.value for b in plan.blocks] == [
        "let",
        "let",
        "where",
        "aggregate",
        "satisfying",
        "projection",
    ]
    (stage,) = view.aggregations
    assert len(view.aggregates) == 1
    uses = view.satisfying_uses(stage.ref)
    assert len(uses) == 3 and all(u.port is uses[0].port for u in uses)
    readiness = stage.authority.source
    assert isinstance(readiness, aggregation.ProjectAggregateGroupedClauseReadiness)
    assert readiness.satisfying is stage.authority.satisfying
    assert len(stage.authority.satisfying_references) == 3
    assert len(readiness.dependency_facts) == 2
    assert (
        readiness.occurrence_facts is not None and len(readiness.occurrence_facts) == 4
    )


def _group_source(*, visible=(), keys=("lhs.id",), family="postgres", kind="query"):
    selected = "".join(
        f"        {name} = {expression}\n" for name, expression in visible
    )
    grouped = "".join(f"        {key}\n" for key in keys)
    return f"""shape Row:
    id: Int not null
    key: Int nullable
source lhs: Row is {family}.table("lhs")
source rhs: Row is {family}.table("rhs")
{kind} result:
    from lhs
    left join rhs as r:
        from lhs
        on lhs.id == r.id
    group by:
{grouped}    select:
{selected}        total = count()
"""


def _ir_product(path: Path, source: str):
    completed = _completed(path, source)
    assert completed.ok, completed.diagnostics
    root = ir.build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(root)
    assert checked.verified, checked.issues
    entry = next(e for e in root.entries if e.owner.definition.name == "result")
    assert isinstance(entry, ir.ProjectIRCompletedQueryBlockOutput)
    return completed, root, entry


@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("visible", ((), (("id", "lhs.id"),)))
def test_ir_preserved_hidden_and_visible_key_cases(
    tmp_path: Path, family, kind, visible
):
    _, root, entry = _ir_product(
        tmp_path, _group_source(visible=visible, family=family, kind=kind)
    )
    (context,) = entry.aggregate_contexts
    assert context.mode is ProjectJoinedAggregationMode.GROUPED
    assert len(context.group_keys) == 1
    grouped = next(
        p.relational
        for p in entry.row_properties
        if p.output.occurrence.producer is context.operator.node
    )
    assert grouped.grain.state is ProjectGrainBasisState.FACTORIZED
    assert len(grouped.grain.active) == 1
    assert bool(grouped.keys) is bool(visible)
    if not visible:
        assert not grouped.fds and not entry.active_properties.relational.keys
    assert tuple(entry.semantic_entry.schema.fields) == (
        *[name for name, _ in visible],
        "total",
    )
    assert any(
        isinstance(origin, ir.ProjectIRQueryBlockGrainOrigin)
        and origin.context is context
        for origin in root.grain_origins.origins
    )


@pytest.mark.parametrize(
    "visible",
    (
        (),
        (("left_id", "lhs.id"),),
        (("right_id", "r.id"), ("left_id", "lhs.id")),
        (("first", "lhs.id"), ("again", "lhs.id")),
    ),
)
def test_ir_two_key_projection_requires_exact_complete_coverage(
    tmp_path: Path, visible
):
    _, _, entry = _ir_product(
        tmp_path, _group_source(keys=("lhs.id", "r.id"), visible=visible)
    )
    (context,) = entry.aggregate_contexts
    assert len(context.group_keys) == 2
    assert context.group_keys[0] is not context.group_keys[1]
    complete = {expr for _, expr in visible} == {"lhs.id", "r.id"}
    assert bool(entry.active_properties.relational.keys) is complete
    if not complete:
        assert not entry.active_properties.relational.fds


@pytest.mark.parametrize(
    "mutation", ("missing", "duplicate", "foreign", "global", "origin")
)
def test_ir_group_context_and_origin_cannot_be_replaced(tmp_path: Path, mutation):
    _, root, entry = _ir_product(
        tmp_path / "local", _group_source(keys=("lhs.id", "r.id"))
    )
    (context,) = entry.aggregate_contexts
    if mutation == "missing":
        object.__setattr__(context, "group_keys", context.group_keys[:1])
    elif mutation == "duplicate":
        object.__setattr__(context, "group_keys", (context.group_keys[0],) * 2)
    elif mutation == "foreign":
        _, _, other = _ir_product(
            tmp_path / "foreign", _group_source(keys=("lhs.id", "r.id"))
        )
        object.__setattr__(
            context, "group_keys", other.aggregate_contexts[0].group_keys
        )
    elif mutation == "global":
        object.__setattr__(context, "mode", ProjectJoinedAggregationMode.GLOBAL)
    else:
        object.__setattr__(root.grain_origins, "origins", ())
    assert not verify_project_query_block_ir(root).verified


@pytest.mark.parametrize("positions", ((), (0,), (1,)))
def test_ir_partial_projection_rejects_forged_visible_key(tmp_path: Path, positions):
    _, root, entry = _ir_product(
        tmp_path / "partial",
        _group_source(keys=("lhs.id", "r.id"), visible=(("left_id", "lhs.id"),)),
    )
    _, _, complete = _ir_product(
        tmp_path / "complete",
        _group_source(
            keys=("lhs.id", "r.id"),
            visible=(("left_id", "lhs.id"), ("right_id", "r.id")),
        ),
    )
    context = entry.aggregate_contexts[0]
    properties = next(
        p.relational
        for p in entry.row_properties
        if p.output.occurrence.producer is context.operator.node
    )
    template = complete.active_properties.relational.keys[0]
    origin = next(
        o
        for o in root.grain_origins.origins
        if isinstance(o, ir.ProjectIRQueryBlockGrainOrigin) and o.context is context
    )
    forged = _graft(
        template,
        output=properties.output,
        determinants=tuple(properties.value_classes[i] for i in positions),
        supports=(context, origin),
    )
    object.__setattr__(properties, "keys", (forged,))
    assert not verify_project_query_block_ir(root).verified


def test_ir_named_hidden_group_does_not_claim_visible_uniqueness(tmp_path: Path):
    source = _group_source(kind="table").replace("table result:", "table grouped:")
    source += """query result:
    from grouped
    select:
        total
"""
    _, root, entry = _ir_product(tmp_path, source)
    upstream = next(e for e in root.entries if e.owner.definition.name == "grouped")
    assert isinstance(upstream, ir.ProjectIRCompletedQueryBlockOutput)
    assert not upstream.active_properties.relational.keys
    assert not entry.active_properties.relational.keys
    assert (
        entry.active_properties.relational.grain.state
        is ProjectGrainBasisState.FACTORIZED
    )


def test_ir_no_join_replay_can_hide_its_group_key(tmp_path: Path):
    source = _group_source(kind="table", visible=(("id", "lhs.id"),)).replace(
        "table result:", "table grouped:"
    )
    source += """query result:
    from grouped
    group by:
        id
    select:
        total = count()
"""
    _, _, entry = _ir_product(tmp_path, source)
    assert isinstance(entry.semantic_entry.root, ir.ProjectConcreteNoJoinReplay)
    assert not entry.active_properties.relational.keys
    assert (
        entry.active_properties.relational.grain.state
        is ProjectGrainBasisState.FACTORIZED
    )


def _joined_aggregates(family="postgres", kind="query"):
    source = _group_source(family=family, kind=kind)
    source = source.replace(
        "    key: Int nullable\n",
        "    key: Int nullable\n    label: Text nullable\n    unique row_key on id\n",
    )
    source = source.replace(
        "    group by:\n        lhs.id\n",
        """    let:
        group_value = lhs.id
        amount = r.key + 1
    where lhs.id > 0
    group by:
        group_value
""",
    )
    return source.replace(
        "        total = count()\n",
        """        row_count = count()
        field_count = count(r.id)
        distinct_labels = count_distinct(r.label)
        total = sum(amount)
        average = avg(amount)
        minimum = min(r.key)
        maximum = max(r.key)
        repeated_total = sum(amount)
    satisfying:
        total > 0 and total > 1 and total < 10
""",
    )


@pytest.mark.parametrize("family,kind", (("postgres", "table"), ("mysql", "query")))
def test_joined_forms_null_extension_repeated_results_and_risks(
    tmp_path: Path, family, kind
):
    _, plan, view = _plan_product(tmp_path, _joined_aggregates(family, kind))
    assert len(view.aggregates) == 8 and len(view.group_keys) == 1
    assert view.arguments_for_aggregate(view.aggregates[0].ref) == ()
    argument = view.arguments_for_aggregate(view.aggregates[1].ref)[0]
    assert argument.value_type.nullability.value == "nullable"
    assert view.aggregates[3].result is not view.aggregates[-1].result
    assert view.aggregates[3].source.item is not view.aggregates[-1].source.item
    (stage,) = view.aggregations
    assert stage.authority.properties.keys == ()
    assert len(stage.authority.risks) == len(view.aggregate_risks)
    assert isinstance(
        stage.authority.source, aggregation.ProjectConcreteJoinedAggregation
    )
    assert len(stage.authority.source.pair_linkages) == 28
    assert all(
        r.source is original
        for r, original in zip(view.aggregate_risks, stage.authority.risks, strict=True)
    )
    uses = view.satisfying_uses(stage.ref)
    assert len(uses) == 3 and all(use.port is uses[0].port for use in uses)
    assert len(view.uses_of(uses[0].port)) == 3
    assert [b.kind.value for b in plan.blocks] == [
        "let",
        "let",
        "where",
        "aggregate",
        "satisfying",
        "projection",
    ]


@pytest.mark.parametrize(
    "call",
    (
        "count(value + 1)",
        "sum(value * 2 + 1)",
        "avg(value + value)",
        "count(len(label))",
        "count_distinct(lower(trim(label)))",
    ),
)
def test_admitted_argument_expressions_keep_actual_nodes(tmp_path: Path, call):
    source = _ordinary(f"    select:\n        total = {call}\n").replace(
        "    value: Int nullable\n",
        "    value: Int nullable\n    label: Text nullable\n",
    )
    _, _, view = _plan_product(tmp_path, source)
    (value,) = view.aggregates
    (argument,) = view.arguments_for_aggregate(value.ref)
    assert argument.expression is aggregation.arguments(value.source)[0]
    if "lower" in call or "len" in call:
        assert isinstance(argument, aggregation.ProjectSQLAggregateArgumentCall)
        assert all(e.site.role.value == "aggregate_argument" for e in view.expressions)


@pytest.mark.parametrize(
    "type_name", ("Bool", "Float", "Decimal", "Text", "Date", "Timestamp", "UUID")
)
def test_count_distinct_preserves_existing_comparison_types(tmp_path: Path, type_name):
    source = _ordinary("    select:\n        total = count_distinct(value)\n").replace(
        "value: Int", f"value: {type_name}"
    )
    _, _, view = _plan_product(tmp_path, source)
    (argument,) = view.arguments_for_aggregate(view.aggregates[0].ref)
    assert argument.value_type.resolved_type.name == type_name
    assert argument.value_type.nullability.value == "nullable"


@pytest.mark.parametrize(
    "call,type_name",
    (
        ("sum", "Decimal"),
        ("avg", "Decimal"),
        ("min", "Date"),
        ("max", "Timestamp"),
        ("min", "Float"),
    ),
)
def test_existing_numeric_and_temporal_result_types(tmp_path: Path, call, type_name):
    source = _ordinary(f"    select:\n        total = {call}(value)\n").replace(
        "value: Int", f"value: {type_name}"
    )
    _, _, view = _plan_product(tmp_path, source)
    assert view.aggregates[0].value_type.resolved_type.name == type_name
    assert view.aggregates[0].value_type.nullability.value == "nullable"


def test_false_input_filter_does_not_erase_global_stage(tmp_path: Path):
    _, plan, view = _plan_product(
        tmp_path, _ordinary("    where false\n    select:\n        total = count()\n")
    )
    assert [b.kind.value for b in plan.blocks] == ["where", "aggregate", "projection"]
    (stage,) = view.aggregations
    assert stage.empty_input is aggregation.ProjectSQLAggregateEmptyInput.ONE_GLOBAL_ROW
    assert stage.inputs and plan.blocks[1].predecessor is plan.blocks[0].ref
    assert len(view.filters) == 1 and len(view.aggregates) == 1


@pytest.mark.parametrize("consumer", ("row", "aggregate", "join"))
def test_named_hidden_group_feeds_immediate_consumers(tmp_path: Path, consumer):
    source = _group_source(kind="table").replace("table result:", "table grouped:")
    source += {
        "row": "query result:\n    from grouped\n    where total > 0\n    select:\n        adjusted = total + 1\n",
        "aggregate": "query result:\n    from grouped\n    select:\n        total = sum(total)\n",
        "join": "query result:\n    from grouped\n    inner join grouped as repeated:\n        from grouped\n        on grouped.total == repeated.total\n    select:\n        first = grouped.total\n        second = repeated.total\n",
    }[consumer]
    roots, plan, view = _plan_product(tmp_path, source)
    grouped = next(
        d for d in view.definitions if d.entry.owner.definition.name == "grouped"
    )
    uses = tuple(
        u
        for u in view.input_uses
        if u.consumer
        is next(d.ref for d in view.definitions if d.entry.owner is roots[2])
    )
    assert uses and all(u.producer is grouped.ref for u in uses)
    assert not grouped.entry.active_properties.relational.keys
    assert len(view.aggregations) == (2 if consumer == "aggregate" else 1)
    assert plan.diagnostics is roots[0].diagnostics


def test_imported_hidden_group_keeps_defining_origin(tmp_path: Path):
    (tmp_path / "a.pietto").write_text(
        _group_source(kind="table").replace("table result:", "table grouped:")
        + "export:\n    table grouped\n"
    )
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table grouped as Public\nexport:\n    table Public\n'
    )
    roots, _, view = _plan_product(
        tmp_path,
        """import "b.pietto":
    table Public as Alias
query result:
    from Alias
    select:
        total
""",
    )
    use = next(u for u in view.input_uses if u.dependency.consumer is roots[2])
    assert [
        hop.facade_occurrence.owning_module_path for hop in use.origin_path.hops
    ] == ["b.pietto", "a.pietto"]
    assert len(view.aggregations) == 1
    assert all(source.module.path == "a.pietto" for source in view.sources)


@pytest.fixture(scope="module")
def aggregation_plans(tmp_path_factory):
    return tuple(
        _plan_product(tmp_path_factory.mktemp("aggregate-plan"), _joined_aggregates())
        for _ in range(2)
    )


@pytest.mark.parametrize(
    "inventory",
    (
        "aggregations",
        "group_keys",
        "aggregates",
        "aggregate_projections",
        "aggregate_risks",
        "origins",
        "demands",
    ),
)
@pytest.mark.parametrize("mutation", ("empty", "duplicate", "foreign"))
def test_aggregate_inventories_are_complete(aggregation_plans, inventory, mutation):
    roots, plan, _ = aggregation_plans[0]
    other = aggregation_plans[1][1]
    values = getattr(plan, inventory)
    changed = (
        ()
        if mutation == "empty"
        else (*values, values[0])
        if mutation == "duplicate"
        else getattr(other, inventory)
    )
    assert not verify_project_sql_plan(
        _graft(plan, **{inventory: changed}), *roots
    ).verified


@pytest.mark.parametrize(
    "inventory,field,replacement",
    (
        ("aggregations", "mode", "global"),
        ("aggregations", "keys", "empty"),
        ("aggregations", "results", "empty"),
        ("aggregations", "empty_input", "global_empty"),
        ("group_keys", "position", "bool"),
        ("group_keys", "source", "foreign"),
        ("group_keys", "input", "result"),
        ("group_keys", "result", "input"),
        ("aggregates", "position", "bool"),
        ("aggregates", "source", "foreign"),
        ("aggregates", "arguments", "empty"),
        ("aggregates", "result", "foreign"),
        ("aggregate_projections", "source", "foreign"),
        ("aggregate_projections", "input", "raw"),
        ("aggregate_projections", "export", "foreign"),
        ("aggregate_risks", "source", "foreign"),
        ("aggregate_risks", "aggregation", "foreign"),
    ),
)
def test_aggregate_witness_fields_are_bound(
    aggregation_plans, inventory, field, replacement
):
    roots, plan, _ = aggregation_plans[0]
    other = aggregation_plans[1][1]
    index = 1 if inventory == "aggregates" else 0
    values = getattr(plan, inventory)
    target = values[index]
    changed = {
        "empty": (),
        "bool": True,
        "global": ProjectJoinedAggregationMode.GLOBAL,
        "global_empty": aggregation.ProjectSQLAggregateEmptyInput.ONE_GLOBAL_ROW,
        "foreign": getattr(getattr(other, inventory)[index], field),
        "raw": plan.input_ports[0].ref,
        "input": getattr(target, "input", None),
        "result": getattr(target, "result", None),
    }[replacement]
    mutated = _graft(target, **{field: changed})
    candidate = _graft(
        plan, **{inventory: (*values[:index], mutated, *values[index + 1 :])}
    )
    assert not verify_project_sql_plan(candidate, *roots).verified


@pytest.mark.parametrize(
    "what",
    (
        "predicate_reference",
        "predicate_type",
        "argument_type",
        "site_scope",
        "result_scope",
    ),
)
def test_aggregate_expression_uses_cannot_capture_foreign_values(
    aggregation_plans, what
):
    roots, plan, view = aggregation_plans[0]
    other = aggregation_plans[1][1]
    site = next(
        s
        for s in plan.expression_sites
        if s.role.value
        == ("aggregate_argument" if what == "argument_type" else "satisfying")
    )
    value = next(e for e in plan.expressions if e.site is site and hasattr(e, "port"))
    foreign = next(
        e for e in other.expressions if e.site.role is site.role and hasattr(e, "port")
    )
    if what == "site_scope":
        changed = _graft(site, block=plan.blocks[0].ref)
        candidate = _graft(
            plan,
            expression_sites=tuple(
                changed if s is site else s for s in plan.expression_sites
            ),
        )
    else:
        changes = (
            {"reference": foreign.reference}
            if what == "predicate_reference"
            else {"port": plan.stage_ports[0].ref}
            if what == "result_scope"
            else {"value_type": _graft(foreign.value_type)}
        )
        changed = _graft(value, **changes)
        candidate = _graft(
            plan,
            expressions=tuple(changed if e is value else e for e in plan.expressions),
        )
    assert not verify_project_sql_plan(candidate, *roots).verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(_graft(view.verification, plan=candidate))


def test_aggregate_inspection_uses_exact_refs(aggregation_plans):
    _, _, view = aggregation_plans[0]
    other = aggregation_plans[1][2]
    with pytest.raises(ValueError, match="belong"):
        view.aggregation(other.aggregations[0].ref)
    with pytest.raises(ValueError, match="belong"):
        view.arguments_for_aggregate(other.aggregates[0].ref)
    with pytest.raises(ValueError, match="belong"):
        view.satisfying_uses(other.aggregations[0].ref)


@pytest.mark.parametrize(
    "body",
    (
        "    group by:\n        id\n    select:\n        id\n",
        "    let:\n        computed = id + 1\n    group by:\n        computed\n    select:\n        total = count()\n",
        "    select:\n        total = sum(sum(value))\n",
        "    select:\n        total = sum(value) + 1\n",
        "    select:\n        id\n        total = sum(value)\n",
        "    select:\n        total = count()\n    satisfying:\n        total > 0\n",
        "    group by:\n        id\n    select:\n        total = count()\n    satisfying:\n        value > 0\n",
    ),
)
def test_invalid_aggregate_combinations_remain_unavailable(tmp_path: Path, body):
    from pietto._project.project_sql_plan import ProjectSQLPlanUnavailable

    roots = _roots(tmp_path, _ordinary(body))
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert not verify_project_sql_plan(result, *roots).verified


def test_joined_unique_aggregate_let_reference_reuses_result(tmp_path: Path):
    source = (
        _joined_aggregates()
        .replace("        repeated_total = sum(amount)\n", "")
        .replace("total > 1", "sum(amount) > 1")
    )
    _, _, view = _plan_product(tmp_path, source)
    uses = view.satisfying_uses(view.aggregations[0].ref)
    assert len(view.aggregates) == 7 and len(uses) == 3
    assert all(use.port is uses[0].port for use in uses)
    assert isinstance(
        uses[1].reference, aggregation.ProjectJoinedSatisfyingAggregateReference
    )


def test_joined_ambiguous_aggregate_call_reference_remains_rejected(tmp_path: Path):
    roots = _roots(
        tmp_path, _joined_aggregates().replace("total > 1", "sum(amount) > 1")
    )
    assert not roots[0].ok
    assert any(d.code == "PIE-S2308" for d in roots[0].diagnostics)


@pytest.mark.parametrize("joined", (False, True))
def test_semantic_group_ordinal_is_not_bool(tmp_path: Path, joined):
    source = (
        _group_source()
        if joined
        else _ordinary(
            "    group by:\n        id\n    select:\n        total = count()\n"
        )
    )
    roots, plan, view = _plan_product(tmp_path, source)
    target = view.group_keys[0].source if joined else view.group_keys[0].reference
    field = "source_ordinal" if joined else "container_ordinal"
    previous = getattr(target, field)
    object.__setattr__(target, field, False)
    try:
        assert not verify_project_sql_plan(plan, *roots).verified
    finally:
        object.__setattr__(target, field, previous)


@pytest.mark.parametrize("joined", (False, True))
def test_satisfying_target_requires_original_output_object(tmp_path: Path, joined):
    body = "    group by:\n        id\n    select:\n        total = sum(value)\n    satisfying:\n        total > 0\n"
    source = _joined_aggregates() if joined else _ordinary(body)
    roots, plan, view = _plan_product(tmp_path / "local", source)
    _, _, other = _plan_product(tmp_path / "foreign", source)
    reference = view.satisfying_uses(view.aggregations[0].ref)[0].reference
    foreign = other.satisfying_uses(other.aggregations[0].ref)[0].reference
    field = "output" if joined else "target_field"
    previous = getattr(reference, field)
    if joined:
        assert isinstance(reference, aggregation.ProjectJoinedSatisfyingOutputReference)
        assert isinstance(foreign, aggregation.ProjectJoinedSatisfyingOutputReference)
        replacement = _graft(foreign.output, item=reference.output.item)
    else:
        assert isinstance(reference, aggregation.ProjectRelationClauseDependencyFact)
        assert isinstance(foreign, aggregation.ProjectRelationClauseDependencyFact)
        replacement = foreign.target_field
    object.__setattr__(reference, field, replacement)
    try:
        assert not verify_project_sql_plan(plan, *roots).verified
    finally:
        object.__setattr__(reference, field, previous)


def test_planning_and_verification_do_not_rebuild_semantics(
    aggregation_plans, monkeypatch
):
    from pietto._project import (
        aggregate_grouped_schema,
        aggregate_grouped_clause_facts,
        project_joined_aggregation,
        project_scalar_namespaces,
    )
    from pietto.semantic import aggregates
    from pietto._project import project_sql_plan_expressions as row

    roots, plan, _ = aggregation_plans[0]

    def forbidden(*args, **kwargs):
        raise AssertionError("Planning or verification rebuilt semantic authority")

    for module, names in (
        (
            aggregate_grouped_schema,
            (
                "semantic_projection_aggregate_result_value_type",
                "build_project_aggregate_grouped_schema_finalization",
            ),
        ),
        (
            aggregate_grouped_clause_facts,
            (
                "check_satisfying_clauses",
                "build_project_aggregate_grouped_clause_readiness",
            ),
        ),
        (
            project_joined_aggregation,
            (
                "_aggregate_attempt",
                "_build_group_protections",
                "_build_grain_linkages",
                "_build_pair_linkages",
                "_require_stage_evidence",
            ),
        ),
        (project_scalar_namespaces, ("resolve_project_joined_namespace_reference",)),
        (aggregates, ("semantic_projection_aggregate_result_value_type",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlan)
    for cls in (
        aggregation.ProjectSQLAggregation,
        aggregation.ProjectSQLAggregate,
        aggregation.ProjectSQLGroupKey,
        aggregation.ProjectSQLAggregateProjection,
        aggregation.ProjectSQLAggregateRisk,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(row, "scalar_nodes", forbidden)
    monkeypatch.setattr(row, "scalar_children", forbidden)
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    assert inspect_project_sql_plan(checked).aggregations is plan.aggregations


@pytest.mark.parametrize(
    "visible",
    ((), (("left_id", "lhs.id"),), (("right_id", "r.id"), ("left_id", "lhs.id"))),
)
def test_ir_self_join_determinants_keep_input_occurrence_identity(
    tmp_path: Path, visible
):
    source = _group_source(keys=("lhs.id", "r.id"), visible=visible).replace(
        "left join rhs as r:", "left join lhs as r:"
    )
    _, _, entry = _ir_product(tmp_path, source)
    assert bool(entry.active_properties.relational.keys) is (len(visible) == 2)
    assert len(entry.aggregate_contexts[0].group_keys) == 2


@pytest.mark.parametrize(
    "visible", ("", "        id\n", "        v = value\n        k = id\n")
)
def test_ir_rebound_group_projection_retains_complete_determinant(
    tmp_path: Path, visible
):
    source = _ordinary(
        """    select:
        id
        value
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
""",
        kind="table",
    ).replace("table result:", "table upstream:")
    source += f"""query result:
    from upstream
    group by:
        id
        value
    select:
{visible}        total = count()
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    root = ir.build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(root)
    assert checked.verified, checked.issues
    entry = next(e for e in root.entries if e.owner.definition.name == "result")
    assert isinstance(entry, ir.ProjectIRReboundExistingOutput)
    assert len(entry.aggregate_contexts[0].group_keys) == 2
    assert bool(entry.active_properties.relational.keys) is ("v = value" in visible)


def test_hidden_group_ir_inspection_keeps_visible_shape(tmp_path: Path):
    from pietto._project.project_query_block_ir_verification import (
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_query_block_ir_inspection import (
        build_project_query_block_ir_inspection,
    )

    _, root, entry = _ir_product(tmp_path, _group_source())
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(root)
    )
    product = build_project_query_block_ir_inspection(bundle)
    assert product.canonical_bytes
    assert tuple(entry.semantic_entry.schema.fields) == ("total",)


@pytest.mark.parametrize(
    "mutation", ("extra_backward", "missing_forward", "foreign_factor", "invented_fd")
)
def test_grouped_grain_and_fd_claims_need_original_premises(tmp_path: Path, mutation):
    from pietto._project.project_grain import ProjectGrainDependencyFact
    from pietto._project.project_ir_relational_properties import ProjectIROutputValueFD
    from pietto._project.project_row_keys import ProjectRowUniquenessStrength

    _, root, entry = _ir_product(
        tmp_path,
        _group_source(keys=("lhs.key",), visible=(("key", "lhs.key"),)).replace(
            "        total = count()\n",
            "        total = count()\n        again = count()\n",
        ),
    )
    context = entry.aggregate_contexts[0]
    properties = next(
        p.relational
        for p in entry.row_properties
        if p.output.occurrence.producer is context.operator.node
    )
    if mutation == "extra_backward":
        extra = ProjectGrainDependencyFact(
            determinants=properties.grain.active,
            dependents=entry.source_properties.grain.active,
        )
        object.__setattr__(
            properties.grain, "dependencies", (*properties.grain.dependencies, extra)
        )
    elif mutation == "missing_forward":
        object.__setattr__(properties.grain, "dependencies", ())
    elif mutation == "foreign_factor":
        object.__setattr__(
            properties.grain, "active", entry.source_properties.grain.active
        )
    else:
        invented = ProjectIROutputValueFD(
            output=properties.output,
            determinants=(properties.value_classes[1],),
            dependents=(properties.value_classes[2],),
            strength=ProjectRowUniquenessStrength.STRICT,
            supports=(context,),
        )
        object.__setattr__(properties, "fds", (*properties.fds, invented))
    assert not verify_project_query_block_ir(root).verified


def test_joined_global_aggregates_keep_existing_relationship_premises(tmp_path: Path):
    from test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage import (
        PROJECT_SOURCE,
    )

    source = (
        PROJECT_SOURCE.split("query absent_stage:", 1)[0]
        + """query result:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        rows = count()
        total = sum(event.metric)
        average = avg(event.metric)
"""
    )
    _, _, view = _plan_product(tmp_path, source)
    assert len(view.aggregates) == 3
    assert view.aggregations[0].mode is ProjectJoinedAggregationMode.GLOBAL
    assert view.aggregate_risks


@pytest.mark.parametrize(
    "role", ("group_key", "aggregate", "aggregate_projection", "aggregate_risk")
)
def test_aggregate_origin_roles_and_demand_sites_are_mandatory(aggregation_plans, role):
    from pietto._project.project_sql_plan import ProjectSQLOriginRole

    roots, plan, _ = aggregation_plans[0]
    index = next(
        i for i, origin in enumerate(plan.origins) if origin.role.value == role
    )
    origin = plan.origins[index]
    changed = _graft(origin, role=ProjectSQLOriginRole.EXPRESSION)
    candidate = _graft(
        plan, origins=(*plan.origins[:index], changed, *plan.origins[index + 1 :])
    )
    assert not verify_project_sql_plan(candidate, *roots).verified
    demand_index = next(
        i for i, demand in enumerate(plan.demands) if demand.subject is origin.subject
    )
    assert not verify_project_sql_plan(
        _graft(
            plan,
            demands=(*plan.demands[:demand_index], *plan.demands[demand_index + 1 :]),
        ),
        *roots,
    ).verified


def test_aggregate_argument_transform_does_not_enable_ordinary_calls(tmp_path: Path):
    from pietto._project.project_sql_plan import ProjectSQLPlanUnavailable

    source = _ordinary("    select:\n        normalized = lower(label)\n").replace(
        "    value: Int nullable\n",
        "    value: Int nullable\n    label: Text nullable\n",
    )
    roots = _roots(tmp_path, source)
    assert roots[0].ok
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert any(
        blocker.kind.value == "call_authority_unavailable"
        for blocker in result.blockers
    )
