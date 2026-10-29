import dataclasses
import json

import pytest

from pietto import cli
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
    # As in every window: the name stands for a value that is no field.
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in checked.diagnostics
    ] == [
        (
            "PIE-S2103",
            "Unsupported window computation for function sum: window order "
            "expression must be a direct field",
            8,
            17,
        )
    ]
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


_NESTED = "Nested aggregate {}() is not supported"
_NOT_DIRECT = (
    "Unsupported window computation for function {{}}: window {} expression "
    "must be a direct field"
)
_UNADMITTED = (
    "Aggregate function {} requires a direct field argument; expression "
    "arguments are not supported yet"
)


# A window keeps the ordinary aggregate argument contract: a call outside it
# reports the ordinary diagnostic there, and `emit-sql` reports it as well
# instead of reaching IR lowering.
@pytest.mark.parametrize(
    ("call", "offset", "code", "message"),
    (
        ("sum(sum(n)) window(order by id)", 4, "PIE-S2311", _NESTED.format("sum")),
        ("sum(count()) window(order by id)", 4, "PIE-S2311", _NESTED.format("count")),
        ("count(sum(n)) window()", 6, "PIE-S2311", _NESTED.format("sum")),
        ("avg(sum(n)) window()", 4, "PIE-S2311", _NESTED.format("sum")),
        ("sum(n + sum(n)) window(order by id)", 8, "PIE-S2311", _NESTED.format("sum")),
        ("sum(None) window(order by id)", 0, "PIE-S2315", _UNADMITTED.format("sum")),
        ("count(None) window()", 0, "PIE-S2315", _UNADMITTED.format("count")),
        ("max(None) window(partition by g)", 0, "PIE-S2315", _UNADMITTED.format("max")),
        ("min(None) window()", 0, "PIE-S2315", _UNADMITTED.format("min")),
        ("avg(None) window()", 0, "PIE-S2315", _UNADMITTED.format("avg")),
        ("sum(nz) window(order by id)", 0, "PIE-S2315", _UNADMITTED.format("sum")),
        ("count(nz) window()", 0, "PIE-S2315", _UNADMITTED.format("count")),
        # A `let:` name whose value is no field is no window key either.
        (
            "sum(n) window(partition by kl)",
            0,
            "PIE-S2103",
            _NOT_DIRECT.format("partition"),
        ),
        ("sum(n) window(order by kc)", 0, "PIE-S2103", _NOT_DIRECT.format("order")),
    ),
)
@pytest.mark.parametrize("hidden", (False, True))
def test_aggregate_window_arguments_keep_the_ordinary_aggregate_diagnostics(
    tmp_path, capsys, call, offset, code, message, hidden
):
    source = (
        "shape Row:\n    id: Int\n    n: Int\n    g: Text\n"
        'source rows: Row = postgres.table("rows")\n'
        "table t:\n    from rows\n"
        "    let nz = None\n    let kl = lower(g)\n    let kc = 3\n"
        "    select:\n        id\n"
        + (f"    qualify:\n        {call} > 0\n" if hidden else f"        x = {call}\n")
    )
    if code == "PIE-S2103":
        message = message.format(call.partition("(")[0])
    expected = (code, message, *((14, 9 + offset) if hidden else (13, 13 + offset)))
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [expected]
    path = tmp_path / "main.pietto"
    path.write_text(source, encoding="utf-8")
    arguments = ["emit-sql", str(path), "--dialect", "postgres", "--format", "json"]
    assert cli.main(arguments) == 1
    assert [
        (
            item["code"],
            item["message"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in json.loads(capsys.readouterr().out)["diagnostics"]
    ] == [expected]


# A window counts a value of a built-in type only, so a field typed by a
# shape, also through an alias, is refused at the call, by `emit-sql` too.
@pytest.mark.parametrize("field", ("home", "maybe", "aliased"))
def test_aggregate_window_count_refuses_a_field_typed_by_a_shape(
    tmp_path, capsys, field
):
    source = (
        "shape Address:\n    city: Text\n"
        "type Place = Address\n"
        "shape Row:\n    id: Int\n    home: Address\n    maybe: Address | None\n"
        "    aliased: Place\n"
        'source rows: Row = postgres.table("rows")\n'
        "table t:\n    from rows\n    select:\n"
        f"        x = count({field}) window()\n"
    )
    expected = [("PIE-S2104", "Invalid arguments for function count", 13, 13)]
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == expected
    path = tmp_path / "main.pietto"
    path.write_text(source, encoding="utf-8")
    arguments = ["emit-sql", str(path), "--dialect", "postgres", "--format", "json"]
    assert cli.main(arguments) == 1
    assert [
        (
            item["code"],
            item["message"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in json.loads(capsys.readouterr().out)["diagnostics"]
    ] == expected


@pytest.mark.parametrize(
    "call",
    (
        "sum(qty) window(order by id)",
        "count(qty) window(order by id)",
        "count(qty) window()",
        "count() window(partition by g)",
        "max(qty) window(partition by g)",
    ),
)
def test_aggregate_window_over_a_row_of_unknown_type_is_refused_as_any_window(call):
    parsed = parse_source(
        'source rows = postgres.table("rows")\n'
        f"table t:\n    from rows\n    select:\n        id\n        x = {call}\n"
    )
    assert parsed.ast is not None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [
        (
            "PIE-S2303",
            "Source rows has no bound shape; row schema is unknown",
            1,
            1,
        ),
        (
            "PIE-S2103",
            f"Unsupported window computation for function {call.partition('(')[0]}: "
            "window input schema must be concrete",
            6,
            13,
        ),
    ]


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
