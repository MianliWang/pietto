"""Contextual row planning through real completion, IR and runtime inspection."""

from pathlib import Path
from typing import cast

import pytest

from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _roots


from dataclasses import replace
from types import MappingProxyType

from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    build_project_sql_plan,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _graft


def _source(body: str, *, kind: str = "query", family: str = "postgres") -> str:
    return f"""shape Row:
    id: Int not null
    key: Int nullable
    flag: Bool nullable
source rows: Row is {family}.table("rows")
{kind} result:
    from rows
{body}"""


def test_real_contextual_type_retention(tmp_path: Path) -> None:
    roots = _roots(
        tmp_path,
        _source("""    let:
        a = id + 1
        b = a * 2
    where b > 0 and flag
    select:
        first = b + a
        second = b
"""),
    )
    assert roots[0].ok, roots[0].diagnostics
    entry = next(e for e in roots[1].root.entries if e.owner is roots[2])
    assert isinstance(entry, ProjectIRReusedEffectiveOutput)
    facts = entry.semantic_entry.fragment.semantic_facts
    scope = facts.let_scope_facts
    assert scope is not None and facts.input_state is not None
    assert scope.definition is not None
    assert scope.definition is roots[2].definition
    assert scope.input_schema is facts.input_state.schema
    assert scope.input_state is facts.input_state
    assert len(scope.expression_value_types) == 6
    assert (
        scope.expression_value_types[scope.bindings[1].expression]
        is scope.value_types["b"]
    )
    assert len(facts.select_expressions) == len(facts.select_facts)
    for fact, selection in zip(
        facts.select_expressions, facts.select_facts, strict=True
    ):
        assert fact.selection is selection and fact.owner is roots[2]
        assert fact.input_schema is scope.input_schema and fact.let_scope is scope
        assert fact.selection.item.expression in fact.expression_value_types
        with pytest.raises(TypeError):
            cast(dict, fact.expression_value_types)[fact.selection.item.expression] = (
                scope.value_types["b"]
            )
    assert facts.where_fact is not None
    assert facts.where_fact.owner is roots[2]
    assert facts.where_fact.clause is scope.definition.where_clause
    assert facts.where_fact.input_schema is scope.input_schema
    assert facts.where_fact.let_scope is scope
    assert len(facts.where_fact.references) == 2
    assert (
        facts.where_fact.expression_value_types[
            facts.where_fact.clause.expression
        ].resolved_type.name
        == "Bool"
    )
    with pytest.raises(TypeError):
        cast(dict, scope.expression_value_types)[scope.bindings[0].expression] = (
            scope.value_types["b"]
        )


@pytest.mark.parametrize(
    ("body", "code"),
    (
        ("    where id\n    select:\n        id\n", "PIE-S2202"),
        ("    where absent > 0\n    select:\n        id\n", "PIE-S2102"),
        ("    select:\n        value = id + true\n", "PIE-S2105"),
        ("    let:\n        id = 1\n    select:\n        value = id\n", "PIE-S2329"),
    ),
)
def test_missed_row_errors_reach_completed(
    tmp_path: Path, body: str, code: str
) -> None:
    roots = _roots(tmp_path, _source(body))
    assert not roots[0].ok
    assert code in [d.code for d in roots[0].diagnostics]
    from pietto._project.project_sql_plan import (
        build_project_sql_plan,
        ProjectSQLPlanUnavailable,
    )

    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_scalar_let_where_vertical(tmp_path: Path, kind: str, family: str) -> None:
    from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
    from pietto._project.project_sql_plan_expressions import ProjectSQLReference

    roots = _roots(
        tmp_path,
        _source(
            """    let:
        a = id + 1
        b = a * 2
    where b > 0 and flag
    select:
        first = b + a
        second = b
        last = 5
""",
            kind=kind,
            family=family,
        ),
    )
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    verification = verify_project_sql_plan(plan, *roots)
    assert verification.verified, verification.issues
    view = inspect_project_sql_plan(verification)
    assert [b.kind.value for b in view.blocks] == ["let", "let", "where", "projection"]
    from pietto.ast_nodes import LetBinding

    bindings = tuple(v.site.occurrence for v in view.let_values)
    assert all(isinstance(binding, LetBinding) for binding in bindings)
    assert [
        binding.name for binding in bindings if isinstance(binding, LetBinding)
    ] == ["a", "b"]
    assert [p.identity.name for p in view.exports] == ["first", "second", "last"]
    assert len(view.filters) == 1 and len(view.input_uses) == 1
    assert all(
        port.ref is not export.ref
        for port in view.stage_ports
        for export in view.exports
    )
    for value in view.expressions:
        assert view.expression(value.ref) is value
        if isinstance(value, ProjectSQLReference):
            assert (
                view.stage_context(value.site.block).lookup(value.symbol.ref).ref
                is value.port
            )
            assert any(use is value for use in view.uses_of(value.port))
    assert [effect.retain_row for effect in view.filters[0].retention_effects] == [
        True,
        False,
        False,
    ]


ROW_BODY = """    let:
        a = rows.id + 1
        b = a * 2
    where b > 0 and flag
    select:
        first = b + a
        again = b
        third = b
        literal = 5
"""


def _product(path: Path, source: str):
    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    verification = verify_project_sql_plan(plan, *roots)
    assert verification.verified, verification.issues
    return roots, plan, inspect_project_sql_plan(verification)


@pytest.fixture(scope="module")
def row_plans(tmp_path_factory: pytest.TempPathFactory):
    return tuple(
        _product(tmp_path_factory.mktemp("row-plan"), _source(ROW_BODY))
        for _ in range(2)
    )


@pytest.mark.parametrize(
    "expression",
    (
        "1",
        "true",
        '"😀\\nquoted\\""',
        "1.25",
        "id",
        "rows.key",
        "-id",
        "+id",
        "id + key",
        "id - 1",
        "id * 2",
        "id % 2",
        "flag and true",
        "flag or false",
        "id == key",
        "id != 0",
        "id <= key",
        "id > key",
        "key is null",
        "id is not null",
        "key between 1 and 9",
    ),
)
def test_closed_scalar_domain_preserves_occurrences(
    tmp_path: Path, expression: str
) -> None:
    roots, plan, view = _product(
        tmp_path,
        _source(
            f"    select:\n        value = {expression}\n        repeated = {expression}\n"
        ),
    )
    assert len(view.projections) == 2
    first, second = view.projections
    assert (
        first.expression is not second.expression and first.export is not second.export
    )
    first_value, second_value = (
        view.expression(first.expression),
        view.expression(second.expression),
    )
    assert first_value.expression is first.semantic.item.expression
    assert second_value.expression is second.semantic.item.expression
    assert first_value.expression is not second_value.expression
    assert view.input_uses and not view.filters and not view.let_values
    assert view.blocks[0].predecessor is view.input_uses[0].ref
    first_site = view.expression_sites[0]
    assert isinstance(first_site, row.ProjectSQLExpressionSite)
    for value in view.expressions:
        assert isinstance(value.site, row.ProjectSQLExpressionSite)
        assert value.site.input_schema is first_site.input_schema

    assert plan.diagnostics is roots[0].diagnostics


def test_nullable_where_and_hidden_dependencies(tmp_path: Path) -> None:
    from pietto.semantic.model import EffectiveNullability

    _, _, view = _product(
        tmp_path, _source("    where flag\n    select:\n        constant = 1\n")
    )
    predicate = view.expression(view.filters[0].predicate)
    assert isinstance(predicate, row.ProjectSQLReference)
    assert predicate.value_type.nullability is EffectiveNullability.NULLABLE
    assert [p.identity.name for p in view.exports] == ["constant"]
    port = view.stage_context(predicate.site.block).lookup(predicate.port)
    assert port.key is predicate.reference.input_field
    from pietto._project.model import ProjectRowField

    assert isinstance(port.key, ProjectRowField)
    assert port.key.name == "flag"
    assert len(view.input_uses) == len(view.sources) == 1
    assert [e.truth.value for e in view.filters[0].retention_effects] == [
        "true",
        "false",
        "unknown",
    ]
    filters = [d for d in view.demands if isinstance(d, row.ProjectSQLFilterDemand)]
    assert len(filters) == 1 and filters[0].value_type is predicate.value_type


def test_let_reuse_crosses_exported_predecessors(row_plans) -> None:
    _, plan, view = row_plans[0]
    assert len(view.let_values) == 2
    a, b = view.let_values
    defined = view.expression(b.expression)
    assert len([e for e in view.expressions if e.expression is defined.expression]) == 1
    selected_refs = [view.expression(p.expression) for p in view.projections[1:3]]
    assert all(isinstance(e, row.ProjectSQLReference) for e in selected_refs)
    assert selected_refs[0].port is selected_refs[1].port
    assert selected_refs[0].ref is not selected_refs[1].ref
    assert plan.exports[1].identity is not plan.exports[2].identity
    ports = {p.ref: p for p in view.stage_ports}
    carried = ports[selected_refs[0].port]
    visited = []
    while carried.ref is not b.port:
        visited.append(carried.block)
        carried = ports[carried.source]
    assert (
        len(visited) == 3
    )  # projection input -> WHERE export -> WHERE input -> LET export
    assert carried.source is b.expression and carried.key is b.site.occurrence
    assert a.site.let_prefix == () and b.site.let_prefix == (a.site.occurrence,)
    assert view.filters[0].site.let_prefix == (a.site.occurrence, b.site.occurrence)


@pytest.mark.parametrize(
    "body",
    (
        "    let:\n        a = b + 1\n        b = id\n    select:\n        value = a\n",
        "    let:\n        a = a + 1\n    select:\n        value = a\n",
        "    let:\n        a = id\n        a = key\n    select:\n        value = a\n",
        "    let:\n        rows = id\n    select:\n        value = id\n",
        "    let:\n        a = id\n    select:\n        a = id\n",
        "    where later > 0\n    select:\n        later = id\n",
        "    select:\n        first = id\n        second = first + 1\n",
    ),
)
def test_existing_visibility_and_collision_rules(tmp_path: Path, body: str) -> None:
    roots = _roots(tmp_path, _source(body))
    assert not roots[0].ok, roots[0].diagnostics
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_unaliased_let_output_keeps_existing_exception(tmp_path: Path) -> None:
    _, _, view = _product(
        tmp_path, _source("    let:\n        a = id + 1\n    select:\n        a\n")
    )
    assert view.exports[0].identity.name == "a"
    assert isinstance(
        view.expression(view.projections[0].expression), row.ProjectSQLReference
    )


@pytest.mark.parametrize("callee", ('trim("hello")',))
def test_call_type_without_callable_authority_is_a_typed_limitation(
    tmp_path: Path, callee: str
) -> None:
    roots = _roots(tmp_path, _source(f"    select:\n        value = {callee}\n"))
    assert roots[0].ok, roots[0].diagnostics
    terminal = build_project_sql_plan(*roots)
    assert isinstance(terminal, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in terminal.blockers] == ["call_authority_unavailable"]
    assert not terminal.diagnostics


def test_named_imported_reexported_scalar_filter_chain(tmp_path: Path) -> None:
    producer = _source(ROW_BODY, kind="table").replace("table result:", "table first:")
    (tmp_path / "producer.pietto").write_text(producer + "export:\n    table first\n")
    (tmp_path / "facade.pietto").write_text(
        'import "producer.pietto":\n    table first as Public\nexport:\n    table Public\n'
    )
    roots, plan, view = _product(
        tmp_path,
        """import "facade.pietto":
    table Public as Input
table next:
    from Input
    where again > 2
    select:
        renamed = first + again
        key = third
query result:
    from next
    let:
        computed = renamed + key
    select:
        final = computed
        repeat = computed
""",
    )
    assert [d.entry.owner.definition.name for d in view.definitions] == [
        "rows",
        "first",
        "next",
        "result",
    ]
    assert len(view.filters) == 2 and len(view.input_uses) == 3
    assert len(view.let_values) == 3 and len(view.all_exports) == 8
    assert [p.identity.name for p in view.exports] == ["final", "repeat"]
    imported = view.input_uses[1]
    assert imported.binding.imported_binding is not None
    assert len(imported.origin_path.hops) == 2
    assert view.sources[0].module.path == "producer.pietto"
    next_definition = view.definitions[2]
    result_input = view.input_uses[2]
    assert all(
        any(p.producer_port is export.ref for export in next_definition.exports)
        for p in result_input.ports
    )
    assert plan.diagnostics is roots[0].diagnostics


@pytest.mark.parametrize("error", (False, True))
def test_unrelated_row_error_versus_valid_later_stage(
    tmp_path: Path, error: bool
) -> None:
    extra = "query unused:\n    from rows\n"
    extra += (
        "    where missing\n    select:\n        id\n"
        if error
        else "    select:\n        id\n    limit 1\n"
    )
    roots = _roots(tmp_path, _source(ROW_BODY) + extra)
    assert roots[0].ok is not error
    result = build_project_sql_plan(*roots)
    if error:
        assert isinstance(result, ProjectSQLPlanUnavailable)
        assert [b.kind.value for b in result.blockers] == [
            "semantic_result_unsuccessful"
        ]
    else:
        assert isinstance(result, ProjectSQLPlan)
        assert verify_project_sql_plan(result, *roots).verified


@pytest.mark.parametrize(
    "section",
    (
        "expression_sites",
        "expressions",
        "operands",
        "stage_ports",
        "let_values",
        "filters",
    ),
)
@pytest.mark.parametrize("change", ("empty", "omit", "duplicate", "reverse", "foreign"))
def test_complete_row_inventory_mutations(row_plans, section: str, change: str) -> None:
    roots, plan, _ = row_plans[0]
    foreign = row_plans[1][1]
    values = getattr(plan, section)
    altered = {
        "empty": (),
        "omit": values[1:],
        "duplicate": (*values, values[0]),
        "reverse": tuple(reversed(values)) if len(values) > 1 else (*values, values[0]),
        "foreign": getattr(foreign, section),
    }[change]
    candidate = _graft(plan, **{section: altered})
    checked = verify_project_sql_plan(candidate, *roots)
    assert not checked.verified, (section, change)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(
            _graft(verify_project_sql_plan(plan, *roots), plan=candidate)
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "site_owner",
        "site_scope",
        "site_input",
        "site_evidence",
        "site_prefix",
        "site_role",
        "foreign_type",
        "other_expression",
        "operand_child",
        "operand_order",
        "reference_fact",
        "old_scope_capture",
        "raw_input_capture",
        "reference_symbol",
        "helper_source",
        "helper_key",
        "helper_type",
        "helper_kind",
        "block_predecessor",
        "block_exports",
        "duplicate_definition",
        "filter_retention",
        "filter_predicate",
        "helper_visible",
    ),
)
def test_context_and_field_level_corruptions(row_plans, mutation: str) -> None:
    roots, plan, _ = row_plans[0]
    foreign = row_plans[1][1]

    def changed(section, index, **fields):
        values = getattr(plan, section)
        return _graft(
            plan,
            **{
                section: (
                    *values[:index],
                    _graft(values[index], **fields),
                    *values[index + 1 :],
                )
            },
        )

    reference_index = next(
        i
        for i, e in enumerate(plan.expressions)
        if isinstance(e, row.ProjectSQLReference)
        and e.site.role is row.ProjectSQLExpressionRole.SELECT
    )
    reference = plan.expressions[reference_index]
    assert isinstance(reference, row.ProjectSQLReference)
    helper_index = next(
        i for i, p in enumerate(plan.stage_ports) if p.ref is plan.let_values[0].port
    )
    mutations = {
        "site_owner": lambda: changed(
            "expression_sites", 0, owner=foreign.scope.selected_owner
        ),
        "site_scope": lambda: changed("expression_sites", 0, block=plan.blocks[-1].ref),
        "site_input": lambda: changed(
            "expression_sites", 0, input_schema=foreign.expression_sites[0].input_schema
        ),
        "site_evidence": lambda: changed(
            "expression_sites", 0, evidence=foreign.expression_sites[0].evidence
        ),
        "site_prefix": lambda: changed(
            "expression_sites", 0, let_prefix=plan.expression_sites[2].let_prefix
        ),
        "site_role": lambda: changed(
            "expression_sites", 0, role=row.ProjectSQLExpressionRole.SELECT
        ),
        "foreign_type": lambda: changed(
            "expressions", 0, value_type=replace(plan.expressions[0].value_type)
        ),
        "other_expression": lambda: changed(
            "expressions", 0, expression=foreign.expressions[0].expression
        ),
        "operand_child": lambda: changed("operands", 0, child=plan.expressions[-1].ref),
        "operand_order": lambda: changed("operands", 0, position=1),
        "reference_fact": lambda: changed(
            "expressions",
            reference_index,
            reference=foreign.expressions[reference_index].reference,
        ),
        "old_scope_capture": lambda: changed(
            "expressions", reference_index, port=plan.let_values[1].port
        ),
        "raw_input_capture": lambda: changed(
            "expressions", reference_index, port=plan.input_ports[0].ref
        ),
        "reference_symbol": lambda: changed(
            "expressions", reference_index, symbol=plan.symbols[0]
        ),
        "helper_source": lambda: changed(
            "stage_ports", helper_index, source=plan.input_ports[0].ref
        ),
        "helper_key": lambda: changed(
            "stage_ports", helper_index, key=plan.let_values[1].site.occurrence
        ),
        "helper_type": lambda: changed(
            "stage_ports",
            helper_index,
            type_evidence=foreign.stage_ports[helper_index].type_evidence,
        ),
        "helper_kind": lambda: changed(
            "stage_ports", helper_index, kind=row.ProjectSQLStagePortKind.INPUT
        ),
        "block_predecessor": lambda: changed(
            "blocks", 2, predecessor=plan.input_uses[0].ref
        ),
        "block_exports": lambda: changed("blocks", 1, exports=plan.blocks[0].exports),
        "duplicate_definition": lambda: changed(
            "let_values", 1, expression=plan.let_values[0].expression
        ),
        "filter_retention": lambda: changed("filters", 0, retention_effects=()),
        "filter_predicate": lambda: changed(
            "filters", 0, predicate=plan.let_values[0].expression
        ),
        "helper_visible": lambda: _graft(
            plan, exports=(*plan.exports, plan.stage_ports[helper_index])
        ),
    }
    candidate = mutations[mutation]()
    assert not verify_project_sql_plan(candidate, *roots).verified, mutation


def test_every_new_origin_and_demand_is_mandatory(row_plans) -> None:
    roots, plan, _ = row_plans[0]
    for section, prefix in (
        ("origins", len(plan.bindings.origins)),
        ("demands", len(plan.bindings.demands)),
    ):
        values = getattr(plan, section)
        for i in range(prefix, len(values)):
            omitted = _graft(plan, **{section: (*values[:i], *values[i + 1 :])})
            assert not verify_project_sql_plan(omitted, *roots).verified, (section, i)
            item = values[i]
            wrong = (
                _graft(item, role=plan.origins[0].role)
                if section == "origins"
                else _graft(item, subject=plan.sources[0].ref)
            )
            candidate = _graft(
                plan, **{section: (*values[:i], wrong, *values[i + 1 :])}
            )
            assert not verify_project_sql_plan(candidate, *roots).verified, (section, i)


def test_missing_or_foreign_contextual_evidence_cannot_remain_positive(
    row_plans,
) -> None:
    roots, plan, _ = row_plans[0]
    _, foreign, _ = row_plans[1]
    evidence = plan.projections[0].site.evidence
    for field, replacement in (
        ("expression_value_types", MappingProxyType({})),
        (
            "expression_value_types",
            foreign.projections[0].site.evidence.expression_value_types,
        ),
        ("input_schema", foreign.projections[0].site.evidence.input_schema),
        ("let_scope", foreign.projections[0].site.evidence.let_scope),
    ):
        original = getattr(evidence, field)
        object.__setattr__(evidence, field, replacement)
        try:
            assert isinstance(
                build_project_sql_plan(*roots), ProjectSQLPlanUnavailable
            ), field
            assert not verify_project_sql_plan(plan, *roots).verified, field
        finally:
            object.__setattr__(evidence, field, original)
    assert verify_project_sql_plan(plan, *roots).verified


def test_exact_stage_queries_and_no_construction_in_readers(
    row_plans, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pietto._project.project_sql_plan as planning
    import pietto._project.module_semantic_fact_preservation as facts
    import pietto._project.let_scope_facts as lets
    import pietto._project.project_completed_semantics as completed
    import pietto._project.project_query_block_ir as ir
    import pietto.semantic.expressions as semantic

    roots, plan, view = row_plans[0]
    foreign = row_plans[1][1]
    for symbol in view.stage_context(plan.blocks[-1].ref).symbols:
        with pytest.raises(ValueError, match="scope"):
            view.stage_context(plan.blocks[0].ref).lookup(symbol.ref)
    with pytest.raises(ValueError, match="belong"):
        view.expression(foreign.expressions[0].ref)
    with pytest.raises(ValueError, match="belong"):
        view.stage_context(foreign.blocks[0].ref)

    def forbidden(*args, **kwargs):
        raise AssertionError("semantic construction or allocation was invoked")

    for module, names in (
        (
            facts,
            (
                "_select_facts",
                "_where_fact",
                "_expression_reference_facts",
                "infer_row_expression",
            ),
        ),
        (
            lets,
            ("analyze_relation_let_bindings", "build_project_relation_let_scope_facts"),
        ),
        (
            completed,
            ("build_project_completed_semantic_result", "_completed_row_references"),
        ),
        (ir, ("build_project_query_block_ir",)),
        (semantic, ("infer_row_expression",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    fresh = build_project_sql_plan(*roots)
    assert isinstance(fresh, ProjectSQLPlan)
    monkeypatch.setattr(planning, "build_project_sql_plan", forbidden)
    monkeypatch.setattr(planning, "build_project_sql_bindings", forbidden)
    monkeypatch.setattr(planning, "_blockers", forbidden)
    monkeypatch.setattr(row, "scalar_nodes", forbidden)
    monkeypatch.setattr(row, "scalar_children", forbidden)
    checked = verify_project_sql_plan(fresh, *roots)
    assert checked.verified, checked.issues
    assert inspect_project_sql_plan(checked).plan is fresh


def test_division_and_unknown_call_preserve_current_nonpositive_rules(
    tmp_path: Path,
) -> None:
    roots = _roots(
        tmp_path / "where", _source("    where id / 2 > 0\n    select:\n        id\n")
    )
    assert roots[0].ok and not roots[0].diagnostics
    terminal = build_project_sql_plan(*roots)
    assert isinstance(terminal, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in terminal.blockers] == [
        "expression_evidence_unavailable"
    ]
    for label, expression in (
        ("division", "id / 2"),
        ("unknown-call", "coalesce(key, 1)"),
    ):
        roots = _roots(
            tmp_path / label, _source(f"    select:\n        value = {expression}\n")
        )
        assert not roots[0].ok
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
    from pietto.parser_api import parse_source

    parsed = parse_source(_source("    select:\n        value = not flag\n"))
    assert parsed.diagnostics and all(d.code == "PIE-P1000" for d in parsed.diagnostics)


def test_replay_context_is_retained_separately_and_set_ancestor_stays_unavailable(
    tmp_path: Path,
) -> None:
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
    )
    from pietto._project.project_final_outputs import ProjectConcreteNoJoinReplay
    from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
        _binding_product,
    )

    source = _source("    select:\n        id\n").split("query result:", 1)[0]
    source += """table repeated:
    union all:
        from rows
        from rows
query result:
    from repeated
    let:
        a = id + 1
        b = a * 2
    where flag and b > 0
    select:
        value = b + a
"""
    roots = _roots(tmp_path, source)
    assert roots[0].ok, roots[0].diagnostics
    entry = next(e for e in roots[1].root.entries if e.owner is roots[2])
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    replay = entry.semantic_entry.root
    assert isinstance(replay, ProjectConcreteNoJoinReplay)
    authority = row.row_authority(roots[0], entry)
    assert isinstance(authority, row.ProjectSQLRowAuthority)
    assert authority.input_schema is replay.input_schema
    assert authority.let_scope is replay.let_scope
    assert replay.semantic_facts.let_scope_facts is not authority.let_scope
    assert authority.where is replay.where.expression_analysis
    assert len(authority.lets) == 2 and len(authority.selected_references[0]) == 2
    assert authority.lets[1].references[0].let_candidates == (
        authority.lets[0].binding,
    )
    assert all(f.scope_facts is replay.let_scope for f in authority.lets)
    assert replay.where.expression_analysis is not None
    assert len(replay.where.expression_analysis.value_types) == 5
    bindings, view = _binding_product(roots)
    assert len(bindings.input_uses) == 3
    assert len(view.definitions) == 3
    terminal = build_project_sql_plan(*roots)
    assert isinstance(terminal, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in terminal.blockers] == ["set_operation"]


@pytest.mark.parametrize("where", ("id", "missing > 0"))
def test_replay_where_error_uses_existing_diagnostics(
    tmp_path: Path, where: str
) -> None:
    source = _source("    select:\n        id\n").split("query result:", 1)[0]
    source += f"""table repeated:
    union all:
        from rows
        from rows
query result:
    from repeated
    where {where}
    select:
        id
"""
    roots = _roots(tmp_path, source)
    assert not roots[0].ok
    assert [d.code for d in roots[0].diagnostics] == [
        "PIE-S2202" if where == "id" else "PIE-S2102"
    ]
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize(
    "mutation", ("let_type_disagreement", "missing_reference", "wrong_input_state")
)
def test_contextual_admission_rejects_inconsistent_retained_evidence(
    row_plans, mutation: str
) -> None:
    roots, plan, _ = row_plans[0]
    scope = plan.expression_sites[0].let_scope
    target, field, replacement = {
        "let_type_disagreement": (
            scope,
            "value_types",
            MappingProxyType(
                {**scope.value_types, "a": replace(scope.value_types["a"])}
            ),
        ),
        "missing_reference": (plan.projections[0].semantic, "references", ()),
        "wrong_input_state": (
            scope,
            "input_state",
            row_plans[1][1].expression_sites[0].let_scope.input_state,
        ),
    }[mutation]
    old = getattr(target, field)
    object.__setattr__(target, field, replacement)
    try:
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified
    finally:
        object.__setattr__(target, field, old)


def test_repeated_filtered_scalar_producer_keeps_binding_graph(tmp_path: Path) -> None:
    from test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols import (
        _binding_product,
    )

    source = _source(ROW_BODY, kind="table").replace("table result:", "table first:")
    source += """table repeated:
    union all:
        from first
        from first
query result:
    from repeated
    select:
        output = first + again
"""
    roots = _roots(tmp_path, source)
    assert roots[0].ok, roots[0].diagnostics
    bindings, view = _binding_product(roots)
    producer = next(
        d for d in view.definitions if d.entry.owner.definition.name == "first"
    )
    repeated = tuple(
        u
        for u in view.input_uses
        if u.dependency.consumer.definition.name == "repeated"
    )
    assert len(repeated) == 2 and repeated[0].ref is not repeated[1].ref
    assert repeated[0].producer is repeated[1].producer is producer.ref
    for index, export in enumerate(producer.exports):
        left, right = repeated[0].ports[index], repeated[1].ports[index]
        assert left.ref is not right.ref
        assert left.producer_port is right.producer_port is export.ref
        assert left.field is right.field is export.field
    assert len(bindings.definitions) == len(bindings.input_uses) == 4
    terminal = build_project_sql_plan(*roots)
    assert isinstance(terminal, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in terminal.blockers] == ["set_operation"]


def test_generated_blocks_partition_the_logical_operator_ledger(row_plans) -> None:
    roots, plan, view = row_plans[0]
    assert [
        [operator.kind.value for operator in block.operators] for block in view.blocks
    ] == [
        ["relation_input"],
        [],
        ["row_filter"],
        ["final_projection"],
    ]
    entry = view.blocks[0].selected
    assert isinstance(entry, ProjectIRReusedEffectiveOutput)
    original = entry.semantic_entry.fragment.logical_stage.operators
    actual = tuple(operator for block in view.blocks for operator in block.operators)
    assert len(actual) == len(original) and all(
        a is b for a, b in zip(actual, original, strict=True)
    )
    wrong = _graft(plan.blocks[1], operators=original)
    candidate = _graft(plan, blocks=(plan.blocks[0], wrong, *plan.blocks[2:]))
    assert not verify_project_sql_plan(candidate, *roots).verified


@pytest.mark.parametrize(
    ("role", "field"),
    (
        ("let", "container_ordinal"),
        ("let", "dependency_ordinal"),
        ("where", "container_ordinal"),
        ("where", "dependency_ordinal"),
        ("select", "container_ordinal"),
        ("select", "dependency_ordinal"),
        ("let", "binding_ordinal"),
        ("select", "selected_output_ordinal"),
    ),
)
def test_contextual_ordinals_require_ints_in_admission_and_verification(
    row_plans, role: str, field: str
) -> None:
    roots, plan, _ = row_plans[0]
    site = next(s for s in plan.expression_sites if s.role.value == role)
    if field == "binding_ordinal":
        target = site.evidence
    elif field == "selected_output_ordinal":
        target = plan.projections[0].semantic
    else:
        target = site.references[0]
    original = getattr(target, field)
    assert type(original) is int and original == 0
    verified = verify_project_sql_plan(plan, *roots)
    assert verified.verified
    object.__setattr__(target, field, False)
    try:
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(verified)
    finally:
        object.__setattr__(target, field, original)
    assert verify_project_sql_plan(plan, *roots).verified
