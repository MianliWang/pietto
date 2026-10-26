import dataclasses

import pytest

from pietto.ast_nodes import NameExpr, TableDef, WindowExpr
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, analyze
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.window_semantics import AggregateWindowAnalysis


SOURCE = """shape Row:
    id: Int
    value: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        running = sum(value) window(order by id)
        all_rows = count() window()
"""


@pytest.mark.parametrize("window_first", (True, False))
def test_grouped_window_sees_complete_string_agg_inputs_regardless_of_select_order(
    window_first: bool,
) -> None:
    select = "        category\n" + (
        "        picked = first_value(summary) window(order by category)\n"
        '        summary = string_agg(label, ",", order by id)\n'
        if window_first
        else '        summary = string_agg(label, ",", order by id)\n'
        "        picked = first_value(summary) window(order by category)\n"
    )
    parsed = parse_source(
        """shape Row:
    id: Int
    category: Int
    label: Text
source rows: Row = postgres.table("rows")
table totals:
    from rows
    group by category
    select:
"""
        + select
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None

    checked = analyze(parsed.ast)

    assert checked.diagnostics == ()
    assert checked.script is not None
    table = next(
        definition
        for definition in checked.script.definitions
        if isinstance(definition, TableDef) and definition.name == "totals"
    )
    picked = next(
        item.expression for item in table.select_items if item.alias == "picked"
    )
    assert isinstance(picked, WindowExpr)
    assert picked in checked.model.window_expression_analyses
    value_type = checked.model.expression_value_types[picked]
    assert value_type.resolved_type.name == "Text"
    assert value_type.nullability is EffectiveNullability.NULLABLE


def test_aggregate_windows_reuse_ordinary_result_contracts_and_allow_default_frames():
    parsed = parse_source(SOURCE)
    assert not parsed.diagnostics
    assert parsed.ast is not None
    result = analyze(parsed.ast)
    assert not result.diagnostics
    analyses = tuple(result.model.aggregate_window_analyses.values())
    assert all(type(item) is AggregateWindowAnalysis for item in analyses)
    assert all(item.semantic_fact.result.value_type is not None for item in analyses)
    assert tuple(
        item.semantic_fact.result.value_type.resolved_type.name
        for item in analyses
        if item.semantic_fact.result.value_type is not None
    ) == (
        "Int",
        "Int",
    )
    assert analyses[1].order_binding_fact is None


@pytest.mark.parametrize(
    ("call", "result"),
    (
        ("sum(value)", "Int"),
        ("count()", "Int"),
        ("count(value)", "Int"),
        ("avg(value)", "Float"),
        ("min(value)", "Int"),
        ("max(value)", "Int"),
    ),
)
def test_every_admitted_aggregate_window_reuses_the_ordinary_result_contract(
    call, result
):
    parsed = parse_source(
        f"""shape Row:
    id: Int
    value: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        value = {call} window(order by id)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert not checked.diagnostics
    analysis = next(iter(checked.model.aggregate_window_analyses.values()))
    assert type(analysis) is AggregateWindowAnalysis
    assert analysis.semantic_fact.result.value_type is not None
    assert analysis.semantic_fact.result.value_type.resolved_type.name == result


@pytest.mark.parametrize("call", ("sum()", "avg()", "min()", "max()", 'sum("x")'))
def test_bad_aggregate_window_arguments_remain_rejected(call):
    parsed = parse_source(
        f"""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        value = {call} window(order by id)
"""
    )
    assert parsed.ast is not None
    assert [diagnostic.code for diagnostic in analyze(parsed.ast).diagnostics] == [
        "PIE-S2104"
    ]


@pytest.mark.parametrize(
    "call",
    (
        "sum(id) ignore nulls",
        "avg(id) from last",
    ),
)
def test_aggregate_windows_reject_inapplicable_authored_modifiers(call):
    parsed = parse_source(
        f"""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        value = {call} window(order by id)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2104"]
    assert not checked.model.aggregate_window_analyses


@pytest.mark.parametrize(
    ("bound", "codes"),
    (
        ("9223372036854775807", ()),
        ("9223372036854775808", ("PIE-S2104",)),
    ),
)
def test_aggregate_window_frame_bounds_keep_the_shared_signed_int64_contract(
    bound, codes
):
    parsed = parse_source(
        f"""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        value = sum(id) window(order by id rows between {bound} preceding and current row)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert tuple(diagnostic.code for diagnostic in checked.diagnostics) == codes


def test_aggregate_window_keeps_result_type_and_hidden_qualify_in_their_exact_maps():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        id
    qualify:
        sum(id) window(order by id rows between 1 preceding and current row) > 0
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert not checked.diagnostics
    expression = next(iter(checked.model.aggregate_window_analyses))
    analysis = checked.model.aggregate_window_analyses[expression]
    assert (
        checked.model.expression_value_types[expression]
        is analysis.semantic_fact.result.value_type
    )
    assert not checked.model.window_expression_analyses
    with pytest.raises(ValueError, match="resolved order"):
        dataclasses.replace(analysis, order_binding_fact=None)


def test_aggregate_window_keeps_single_file_admission_and_ordinary_let_contracts():
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let shifted = id + 1
    select:
        value = sum(shifted) window(order by id)
"""
    parsed = parse_source(source)
    assert parsed.ast is not None
    single_file = analyze(parsed.ast)
    assert not single_file.diagnostics
    assert single_file.model.aggregate_window_analyses
    project = analyze_project_namespace(parsed.ast)
    assert [diagnostic.code for diagnostic in project.diagnostics] == ["PIE-S2103"]
    assert not project.model.aggregate_window_analyses


def test_min_window_preserves_the_ordinary_single_file_let_rejection():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let alias = id
    select:
        value = min(alias) window(order by id)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2104"]
    assert not checked.model.aggregate_window_analyses


def test_aggregate_window_does_not_expand_a_computed_let_in_its_specification():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let shifted = id + 1
    select:
        value = sum(id) window(order by shifted)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2102"]
    assert not checked.model.aggregate_window_analyses


def test_aggregate_window_does_not_add_an_argument_error_to_a_failed_let_read():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let broken = missing
    select:
        value = sum(broken) window(order by id)
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2102"]


def test_aggregate_window_count_preserves_the_ordinary_unknown_source_contract():
    parsed = parse_source(
        """source rows = postgres.table("rows")
table totals:
    from rows
    select:
        value = count(x) window()
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2303"]
    analysis = next(iter(checked.model.aggregate_window_analyses.values()))
    assert analysis.semantic_fact.result.value_type is not None
    assert analysis.semantic_fact.result.value_type.resolved_type.name == "Int"


def test_aggregate_window_count_keeps_an_explained_unknown_unavailable():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        value = count(missing) window()
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2102"]
    assert not checked.model.aggregate_window_analyses


def test_hidden_unavailable_aggregate_window_keeps_its_argument_diagnostic_only():
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        id
    qualify:
        sum(missing) window() > 0
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert [diagnostic.code for diagnostic in checked.diagnostics] == ["PIE-S2102"]
    window = next(
        item
        for item in checked.model.expression_value_types
        if type(item) is WindowExpr
    )
    assert checked.model.expression_value_types[window].kind.value == "unknown"


@pytest.mark.parametrize("call", ("first_value(id)", "sum(id)"))
@pytest.mark.parametrize(
    ("bound", "codes"),
    (
        ("9223372036854775807", ()),
        ("9223372036854775808", ("PIE-S2104",)),
        ("-1", ("PIE-S2104",)),
        ("id", ("PIE-S2104",)),
    ),
)
@pytest.mark.parametrize("hidden", (False, True))
def test_hidden_qualify_and_selected_windows_share_single_file_frame_literal_ranges(
    call, bound, codes, hidden
):
    window = (
        f"{call} window(order by id rows between {bound} preceding and current row)"
    )
    body = (
        f"    select:\n        id\n    qualify:\n        {window} > 0\n"
        if hidden
        else f"    select:\n        value = {window}\n"
    )
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
"""
        + body
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert tuple(diagnostic.code for diagnostic in checked.diagnostics) == codes


@pytest.mark.parametrize("call", ("first_value(id)", "sum(id)"))
@pytest.mark.parametrize("site", ("selected", "hidden", "named"))
@pytest.mark.parametrize("ordered", (False, True))
def test_groups_frames_require_order_for_old_and_aggregate_windows(call, site, ordered):
    order = " order by id" if ordered else ""
    frame = "groups between unbounded preceding and current row"
    window = f"{call} window({order.strip()} {frame})"
    if site == "selected":
        body = f"    select:\n        value = {window}\n"
    elif site == "hidden":
        body = f"    select:\n        id\n    qualify:\n        {window} > 0\n"
    else:
        body = (
            f"    let frame = window({order.strip()} {frame})\n"
            "    select:\n"
            f"        value = {call} window frame\n"
        )
    parsed = parse_source(
        """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
"""
        + body
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert tuple(diagnostic.code for diagnostic in checked.diagnostics) == (
        () if ordered else ("PIE-S2103" if call == "first_value(id)" else "PIE-S2104",)
    )


def test_hidden_aggregate_windows_keep_a_qualified_join_group_key_origin():
    parsed = parse_source(
        """shape Row:
    id: Int
    row_key = unique(id)
    label: Text
    amount: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    let right = rows
    inner join right on rows.id == right.id
    group by rows.label
    select:
        key = rows.label
        total = sum(right.amount)
    qualify:
        sum(total) window(order by key) > 0 and count(len(key)) window(order by key) > 0
"""
    )
    assert parsed.ast is not None
    checked = analyze(parsed.ast)
    assert not checked.diagnostics
    analyses = tuple(checked.model.aggregate_window_analyses.values())
    assert len(analyses) == 2
    assert all(analysis.order_binding_fact is not None for analysis in analyses)
    for analysis in analyses:
        assert analysis.order_binding_fact is not None
        names: list[str] = []
        for binding in analysis.order_binding_fact.bindings:
            assert isinstance(binding.expression, NameExpr)
            names.append(binding.expression.name)
        assert tuple(names) == ("key",)
