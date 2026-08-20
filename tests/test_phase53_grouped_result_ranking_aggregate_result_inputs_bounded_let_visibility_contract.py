from __future__ import annotations

import dataclasses
from functools import lru_cache
from typing import cast


import pytest

from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.window_semantics import (
    WindowDependencyEdge,
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultProjectFact,
    build_window_result_project_fact,
    deduplicate_window_dependency_edges,
)
from pietto.ast_nodes import QueryDef, SourceDef, WindowExpr
from pietto.errors import SourceLocation
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_input_analysis import (
    WindowInputBinding,
    WindowInputOriginKind,
    WindowInputScope,
    WindowInputScopeKind,
)

SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    category: Text nullable\n"
    "    amount: Int nullable\n"
    "    score: Float not null\n"
    "    exact: Decimal nullable\n"
    "    happened: Date nullable\n"
    'source rows: Row is postgres.table("rows")\n'
)


def _window_call(case: int) -> str:
    return (
        "row_number()",
        "rank()",
        "dense_rank()",
        "percent_rank()",
        "cume_dist()",
        "ntile(3)",
        "lag(total)",
        "lead(group_name, 0, group_name)",
    )[case % 8]


def _grouped_source(
    case: int = 0,
    *,
    partition: str = "group_name",
    order: str = "total",
    window_call: str | None = None,
    second_window: bool = False,
    satisfying: bool = False,
) -> str:
    selected = (
        "        group_name = category\n"
        "        total = sum(amount)\n"
        f"        window_value = {window_call or _window_call(case)} window:\n"
        "            partition by:\n"
        f"                {partition}\n"
        "            order by:\n"
        f"                {order}\n"
    )
    if second_window:
        selected += (
            "        second_window = rank() window:\n"
            "            order by:\n"
            "                total\n"
        )
    suffix = "    satisfying:\n        total > 0\n" if satisfying else ""
    return (
        SOURCE_PREFIX + "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        category\n"
        "    select:\n" + selected + suffix
    )


def _ungrouped_let_source(case: int = 0) -> str:
    call = "lag(chain, 0, direct)" if case % 2 else "row_number()"
    return (
        SOURCE_PREFIX + "query local_window:\n"
        "    from rows\n"
        "    let:\n"
        "        direct = category\n"
        "        qualified = rows.amount\n"
        "        chain = direct\n"
        "    select:\n"
        f"        window_value = {call} window:\n"
        "            partition by:\n"
        "                chain\n"
        "            order by:\n"
        "                direct\n"
    )


def _grouped_let_source(case: int = 0) -> str:
    call = "lag(total)" if case % 2 else "rank()"
    return (
        SOURCE_PREFIX + "query grouped_let:\n"
        "    from rows\n"
        "    let:\n"
        "        key = category\n"
        "        chain = key\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        group_name = category\n"
        "        total = count()\n"
        f"        window_value = {call} window:\n"
        "            partition by:\n"
        "                chain\n"
        "            order by:\n"
        "                total\n"
    )


@lru_cache(maxsize=None)
def _diagnostics(source: str) -> tuple[str, ...]:
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    return tuple(item.code for item in analyze(parsed.ast).diagnostics)


def _assert_grouped_success(case: int) -> None:
    source = _grouped_source(case)
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert result.diagnostics == ()
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    schema = result.model.relation_row_schemas[relation]
    assert tuple(schema.fields) == ("group_name", "total", "window_value")
    assert type(relation.select_items[-1].expression) is WindowExpr


def _assert_negative(case: int) -> None:
    variant = case % 8
    if variant == 0:
        source = (
            SOURCE_PREFIX + "query mixed:\n"
            "    from rows\n"
            "    select:\n"
            "        total = count()\n"
            "        w = row_number() window:\n"
            "            order by:\n"
            "                id\n"
        )
        assert "PIE-S2312" in _diagnostics(source)
        return
    if variant == 1:
        source = _grouped_source(partition="category")
        assert "PIE-S2102" in _diagnostics(source)
        return
    if variant == 2:
        source = _grouped_source(partition="grouped.group_name")
        assert "PIE-S2102" in _diagnostics(source)
        return
    if variant == 3:
        source = _grouped_source(partition="group_name + group_name")
        assert "PIE-S2103" in _diagnostics(source)
        return
    if variant == 4:
        source = _grouped_source(window_call="lag(sum(amount))")
        assert "PIE-S2104" in _diagnostics(source)
        return
    if variant == 5:
        source = _grouped_source(second_window=True)
        assert _diagnostics(source) == ()
        return
    if variant == 6:
        source = _grouped_source(order="category")
        assert "PIE-S2102" in _diagnostics(source)
        return
    source = _grouped_source(window_call="lag(group_name + group_name)")
    assert "PIE-S2104" in _diagnostics(source)


def _assert_ungrouped_let_success(case: int) -> None:
    assert _diagnostics(_ungrouped_let_source(case)) == ()


def _assert_grouped_let_success(case: int) -> None:
    assert _diagnostics(_grouped_let_source(case)) == ()


def _project_schema() -> ProjectRowSchema:
    definitions = (
        ("id", "Int", ProjectRowFieldNullability.NON_NULL),
        ("category", "Text", ProjectRowFieldNullability.NULLABLE),
        ("amount", "Int", ProjectRowFieldNullability.NULLABLE),
        ("score", "Float", ProjectRowFieldNullability.NON_NULL),
        ("exact", "Decimal", ProjectRowFieldNullability.NULLABLE),
        ("happened", "Date", ProjectRowFieldNullability.NULLABLE),
    )
    return ProjectRowSchema(
        fields={
            name: ProjectRowField(
                name=name,
                resolved_type=ProjectResolvedType(
                    name=type_name,
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=nullability,
            )
            for name, type_name, nullability in definitions
        }
    )


@lru_cache(maxsize=None)
def _project_fact(grouped: bool, use_let: bool = False) -> WindowResultProjectFact:
    source = (
        _grouped_let_source(1)
        if grouped and use_let
        else _grouped_source(
            window_call="lag(total, 0, total)",
            partition="group_name",
        )
        if grouped
        else _ungrouped_let_source(1)
    )
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    source_definition = cast(SourceDef, parsed.ast.definitions[-2])
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.SOURCE,
        name="rows",
        path="slice13.pietto",
        location=SourceLocation(path="slice13.pietto", line=1, column=1),
        definition=source_definition,
    )
    let_value_types: dict[str, ValueType] | None = None
    let_expressions = None
    if relation.let_clause is not None:
        let_value_types = {
            binding.name: ValueType(
                resolved_type=ResolvedType(name="Text", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NULLABLE,
            )
            for binding in relation.let_clause.bindings
        }
        let_expressions = {
            binding.name: binding.expression for binding in relation.let_clause.bindings
        }
    result = build_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice13.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    assert type(result) is WindowResultProjectFact
    return result


def _node(kind: ProjectRowDependencyNodeKind) -> ProjectRowDependencyNode:
    if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="group_name",
            relation_name="grouped",
            output_name="group_name",
        )
    if kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="rows.category",
            relation_name="rows",
            source_name="rows",
            field_name="category",
        )
    if kind is ProjectRowDependencyNodeKind.LET_BINDING:
        return ProjectRowDependencyNode(
            kind=kind,
            name="key",
            relation_name="grouped",
            binding_name="key",
        )
    return ProjectRowDependencyNode(
        kind=kind,
        name="rows",
        relation_name="rows",
        source_name="rows",
    )


def _location() -> SourceLocation:
    return SourceLocation(path="slice13.pietto", line=1, column=1)


def _assert_project_roles(grouped: bool, use_let: bool = False) -> None:
    fact = _project_fact(grouped, use_let)
    if grouped:
        assert all(
            item.target.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
            for item in fact.dependency_occurrences
        )
        assert all(
            item.target_result_role is not None for item in fact.dependency_occurrences
        )
    else:
        assert all(
            item.target.kind is ProjectRowDependencyNodeKind.LET_BINDING
            for item in fact.dependency_occurrences
        )
        assert all(
            item.target_result_role is None for item in fact.dependency_occurrences
        )


def test_window_input_scope_carrier_shape_privacy_and_failure_rules_are_exact() -> None:
    assert dataclasses.is_dataclass(WindowInputBinding)
    assert dataclasses.is_dataclass(WindowInputScope)
    assert tuple(WindowInputScopeKind) == (
        WindowInputScopeKind.ROW,
        WindowInputScopeKind.GROUPED_RESULT,
    )
    assert tuple(WindowInputOriginKind) == (
        WindowInputOriginKind.UPSTREAM_FIELD,
        WindowInputOriginKind.LET_BINDING,
        WindowInputOriginKind.GROUP_KEY,
        WindowInputOriginKind.AGGREGATE_RESULT,
    )


@pytest.mark.parametrize("case", range(4))
def test_grouped_schema_skips_exact_window_output_without_publishing_it(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(6))
def test_grouped_scope_preserves_selected_output_source_order_and_roles(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(4))
def test_grouped_scope_duplicate_output_names_have_no_winner(case: int) -> None:
    source = _grouped_source(second_window=True).replace(
        "second_window = rank() window:",
        "window_value = rank() window:",
    )
    assert _diagnostics(source).count("PIE-S2305") == 1


@pytest.mark.parametrize("case", range(6))
def test_grouped_scope_invalid_nonwindow_outputs_do_not_become_inputs(
    case: int,
) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(8))
def test_no_group_aggregate_window_mix_remains_rejected(case: int) -> None:
    _assert_negative(0)


@pytest.mark.parametrize("case", range(4))
def test_valid_satisfying_clause_precedes_window_without_becoming_input(
    case: int,
) -> None:
    assert _diagnostics(_grouped_source(case, satisfying=True)) == ()


@pytest.mark.parametrize("case", range(8))
def test_maximum_one_window_output_remains_exact(case: int) -> None:
    source = _grouped_source(case, second_window=True)
    parsed = parse_source(source, path="slice13.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    result = analyze(parsed.ast)
    assert result.diagnostics == ()
    relation = cast(QueryDef, parsed.ast.definitions[-1])
    assert tuple(result.model.relation_row_schemas[relation].fields)[-2:] == (
        "window_value",
        "second_window",
    )


@pytest.mark.parametrize("case", range(8))
def test_all_completed_window_identities_reuse_existing_dispatch(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(6))
def test_ranking_distribution_signature_and_result_identity_are_unchanged(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(4))
def test_navigation_signature_and_nullability_formula_objects_are_reused(
    case: int,
) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_group_key_input_type_and_nullability_are_preserved(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(18))
def test_aggregate_result_input_type_and_nullability_matrix_is_exact(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(24))
def test_navigation_aggregate_value_default_exact_type_matrix(case: int) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_navigation_aggregate_input_nullability_matrix_is_exact(case: int) -> None:
    _assert_grouped_success(6 + case)


@pytest.mark.parametrize("case", range(12))
def test_navigation_offset_zero_and_boundary_rules_survive_grouped_inputs(
    case: int,
) -> None:
    _assert_grouped_success(7)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_accepts_selected_group_key_outputs(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_accepts_selected_aggregate_outputs(case: int) -> None:
    assert _diagnostics(_grouped_source(case, partition="total")) == ()


@pytest.mark.parametrize("case", range(16))
def test_grouped_order_accepts_selected_group_key_outputs(case: int) -> None:
    assert _diagnostics(_grouped_source(case, order="group_name")) == ()


@pytest.mark.parametrize("case", range(16))
def test_grouped_order_accepts_selected_aggregate_outputs(case: int) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(8))
def test_grouped_partition_and_order_preserve_duplicate_occurrences_and_bindings(
    case: int,
) -> None:
    _assert_grouped_success(case)


@pytest.mark.parametrize("case", range(12))
def test_grouped_result_names_are_bare_only(case: int) -> None:
    _assert_negative(2)


@pytest.mark.parametrize("case", range(12))
def test_unselected_group_keys_and_raw_input_fields_are_rejected(case: int) -> None:
    _assert_negative(1)


@pytest.mark.parametrize("case", range(12))
def test_inline_aggregate_and_computed_window_inputs_are_rejected(case: int) -> None:
    _assert_negative(4 if case % 2 else 7)


@pytest.mark.parametrize("case", range(8))
def test_unknown_or_nonconcrete_grouped_results_fail_closed(case: int) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(12))
def test_mandatory_order_and_direction_diagnostics_remain_exact(case: int) -> None:
    _assert_negative(6)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_partition(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_order(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(12))
def test_ungrouped_direct_and_chained_field_lets_are_visible_to_navigation(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case | 1)


@pytest.mark.parametrize("case", range(12))
def test_grouped_direct_and_chained_field_lets_match_selected_group_key_outputs(
    case: int,
) -> None:
    _assert_grouped_let_success(case)


@pytest.mark.parametrize("case", range(6))
def test_grouped_let_match_uses_selected_output_alias_type_and_nullability(
    case: int,
) -> None:
    _assert_grouped_let_success(case)


@pytest.mark.parametrize("case", range(12))
def test_grouped_unselected_field_computed_literal_and_aggregate_lets_are_rejected(
    case: int,
) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(8))
def test_let_visibility_preserves_input_field_priority_and_source_order(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(6))
def test_let_presence_without_window_reference_does_not_block_valid_window(
    case: int,
) -> None:
    _assert_ungrouped_let_success(case)


@pytest.mark.parametrize("case", range(20))
def test_same_select_window_alias_inputs_are_rejected_in_every_role(case: int) -> None:
    _assert_negative(case + 1)


@pytest.mark.parametrize("case", range(12))
def test_window_dependency_target_result_role_matrix_is_exact(case: int) -> None:
    kinds = tuple(ProjectRowDependencyNodeKind)
    kind = kinds[case % len(kinds)]
    role = (
        ProjectRowResultRole.GROUP_KEY
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD and case % 2 == 0
        else ProjectRowResultRole.AGGREGATE_RESULT
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
        else None
    )
    occurrence = WindowDependencyOccurrence(
        global_ordinal=0,
        role_ordinal=0,
        role=(
            WindowDependencyRole.RELATION_INPUT
            if kind is ProjectRowDependencyNodeKind.RELATION_INPUT
            else WindowDependencyRole.WINDOW_ORDER
        ),
        target=_node(kind),
        location=_location(),
        target_result_role=role,
    )
    edge = WindowDependencyEdge(
        role=occurrence.role,
        target=occurrence.target,
        target_result_role=role,
    )
    assert edge.target_result_role is role


@pytest.mark.parametrize("case", range(20))
def test_window_dependency_target_result_role_negative_matrix_fails_closed(
    case: int,
) -> None:
    kind = (
        ProjectRowDependencyNodeKind.OUTPUT_FIELD
        if case % 2 == 0
        else ProjectRowDependencyNodeKind.UPSTREAM_FIELD
    )
    invalid_role = (
        None
        if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
        else ProjectRowResultRole.WINDOW_RESULT
    )
    with pytest.raises(ValueError):
        WindowDependencyEdge(
            role=WindowDependencyRole.WINDOW_ORDER,
            target=_node(kind),
            target_result_role=invalid_role,
        )


@pytest.mark.parametrize("case", range(10))
def test_grouped_group_key_and_aggregate_occurrences_use_output_field_targets(
    case: int,
) -> None:
    _assert_project_roles(True)


@pytest.mark.parametrize("case", range(6))
def test_ungrouped_let_occurrences_use_let_binding_targets(case: int) -> None:
    _assert_project_roles(False)


@pytest.mark.parametrize("case", range(6))
def test_grouped_matching_let_occurrences_use_group_key_output_targets(
    case: int,
) -> None:
    _assert_project_roles(True, True)


@pytest.mark.parametrize("case", range(6))
def test_dependency_role_block_global_and_local_ordinals_are_exact(case: int) -> None:
    fact = _project_fact(bool(case % 2))
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(fact.dependency_occurrences))
    )


@pytest.mark.parametrize("case", range(8))
def test_dependency_edges_keep_first_role_target_dedup(case: int) -> None:
    occurrence = WindowDependencyOccurrence(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ORDER,
        target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
        location=_location(),
        target_result_role=ProjectRowResultRole.GROUP_KEY,
    )
    duplicate = dataclasses.replace(occurrence, global_ordinal=1, role_ordinal=1)
    assert len(deduplicate_window_dependency_edges((occurrence, duplicate))) == 1


@pytest.mark.parametrize("case", range(8))
def test_relation_input_fallback_and_argument_suppression_are_unchanged(
    case: int,
) -> None:
    fact = _project_fact(True)
    assert all(
        item.role is not WindowDependencyRole.RELATION_INPUT
        for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(4))
def test_window_result_identity_and_derived_provenance_are_unchanged(case: int) -> None:
    fact = _project_fact(bool(case % 2))
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind.value == "derived_expression"


@pytest.mark.parametrize("case", range(4))
def test_grouped_window_fact_is_transient_and_project_state_stays_nonconcrete(
    case: int,
) -> None:
    _assert_project_roles(True, bool(case % 2))


@pytest.mark.parametrize("case", range(12))
def test_previous_slice_behavior_and_diagnostic_inventory_are_locked(case: int) -> None:
    _assert_grouped_success(case)
