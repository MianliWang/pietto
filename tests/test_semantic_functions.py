from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    Expression,
    MembershipExpr,
    Script,
    TableDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

SOURCE = (
    "shape User:\n"
    "    email: Text | None\n"
    "    count: Int\n"
    'source users: User = postgres.table("users")\n'
)


@pytest.mark.parametrize("function_name", ["lower", "trim"])
def test_text_transform_function_returns_text(function_name: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = {function_name}(email)\n"
        )
    )
    expression = _call(result)
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.resolved_type.name == "Text"
    assert value_type.nullability is EffectiveNullability.NULLABLE


def test_nested_lower_trim_returns_text_and_records_inner_call() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(trim(email))\n"
        )
    )
    expression = _call(result)
    inner = expression.arguments[0]
    assert isinstance(inner, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"
    assert result.model.expression_value_types[inner].resolved_type.name == "Text"


def test_len_returns_int() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        length = len(email)\n"
        )
    )
    expression = _call(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Int"


def test_c5_scalar_functions_keep_their_approved_types() -> None:
    result = analyze(
        _parse(
            "shape Values:\n"
            "    id: Int\n"
            "    amount: Decimal\n"
            "    ratio: Float\n"
            "    opened_on: Date | None\n"
            "    opened_at: Timestamp\n"
            'source values: Values = postgres.table("values")\n'
            "table projected:\n"
            "    from values\n"
            "    let scale = 2\n"
            '    let unit = "month"\n'
            "    select:\n"
            "        decimal = round(amount, scale)\n"
            "        float = round(ratio)\n"
            "        day = date_trunc(unit, opened_on)\n"
            '        minute = date_trunc("minute", opened_at)\n'
            "        id_text = Text(id)\n"
        )
    )
    table = _table(result)

    assert result.diagnostics == ()
    assert [
        result.model.expression_value_types[item.expression].resolved_type.name
        for item in table.select_items
    ] == ["Decimal", "Float", "Date", "Timestamp", "Text"]
    assert (
        result.model.expression_value_types[
            table.select_items[2].expression
        ].nullability
        is EffectiveNullability.NULLABLE
    )


def test_string_agg_checks_a_known_bad_delimiter_beside_an_unknown_value() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        summary = string_agg(None, count, order by count)\n"
        )
    )

    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-S2104",
            "Invalid arguments for aggregate string_agg: expected two Text arguments",
        )
    ]


@pytest.mark.parametrize(
    "expression",
    [
        "lower(email, order by count)",
        "Text(count, order by missing)",
        "f(count, order by missing)",
        "sum(count, order by count)",
        "lag(count, order by count) window(order by count)",
    ],
)
def test_internal_order_is_refused_outside_ordinary_string_agg(expression: str) -> None:
    prefix = (
        "def f(value: Int) -> Int:\n    return value\n"
        if expression.startswith("f(")
        else ""
    )
    result = analyze(
        _parse(
            prefix + SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = {expression}\n"
        )
    )

    assert any(
        item.code == "PIE-S2104" and "Internal ORDER BY" in item.message
        for item in result.diagnostics
    )


def test_string_agg_remains_legal_beside_an_unrelated_def() -> None:
    result = analyze(
        _parse(
            "def f(value: Int) -> Int:\n    return value\n"
            + SOURCE
            + "table projected:\n"
            "    from users\n"
            "    select:\n"
            '        summary = string_agg(email, ",", order by count desc, count)\n'
        )
    )

    assert result.diagnostics == ()


def test_text_constructor_keeps_authored_def_priority_and_rejects_non_int() -> None:
    shadowed = analyze(
        _parse(
            "def Text(value: Int) -> Int:\n    return value\n"
            + SOURCE
            + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = Text(count)\n"
        )
    )
    expression = _table(shadowed).select_items[0].expression

    assert shadowed.diagnostics == ()
    assert shadowed.model.expression_value_types[expression].resolved_type.name == "Int"

    refused = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = Text(email)\n"
        )
    )
    assert [(item.code, item.message) for item in refused.diagnostics] == [
        (
            "PIE-S2105",
            "Invalid cast from Text to Text: "
            "only Int-to-Text conversion is supported; write Text(expression)",
        )
    ]


@pytest.mark.parametrize(
    ("value", "source"),
    (
        ("None", "null"),
        ("1.5", "Float"),
    ),
)
def test_text_constructor_reports_its_own_conversion_hint(
    value: str, source: str
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = Text({value})\n"
        )
    )

    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-S2105",
            f"Invalid cast from {source} to Text: "
            "only Int-to-Text conversion is supported; write Text(expression)",
        )
    ]


def test_matches_returns_bool_and_is_valid_where_predicate() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            '    where matches(email, "^[a-z]+$")\n'
            "    select:\n"
            "        email\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_unknown_function_reports_pie_s2103() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = normalize(email)\n"
        )
    )
    expression = _call(result)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2103", Severity.ERROR, "Unknown function: normalize")]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


_AGGREGATES = "the available aggregates are avg, count, count_distinct, max, min, string_agg and sum"
_COLLECT = (
    "a Collect read is the select item `name = collect relation` in an "
    "EXPLICIT_MODULES project"
)


@pytest.mark.parametrize(
    ("call", "hint"),
    [
        ("length(email)", "use `len(Text)` instead"),
        ("char_length(email)", "use `len(Text)` instead"),
        ('concat(email, "!")', "string concatenation is not supported yet"),
        (
            "generate_series(1, 3, 1)",
            "it is a table function, read with `from generate_series(start, stop, "
            "step) as n` in an EXPLICIT_MODULES project",
        ),
        ("stddev(count)", _AGGREGATES),
        ("mean(count)", _AGGREGATES),
        # D71.01/D71.02: the nested-relation spellings are no calls.
        ("collect(email)", _COLLECT),
        ("list(email)", _COLLECT),
        (
            "unnest(email)",
            "an Unnest is `let o = unnest(binding.field)` that a later JOIN of the "
            "same body reads, in an EXPLICIT_MODULES project",
        ),
        # A name written with capitals gets the hint of its lowercase spelling.
        ("LENGTH(email)", "use `len(Text)` instead"),
        ("Median(count)", _AGGREGATES),
    ],
)
def test_unknown_function_of_a_sql_or_python_habit_names_the_pietto_form(
    call: str, hint: str
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = {call}\n"
        )
    )

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == [("PIE-S2103", 8, 17, f"Unknown function: {call.split('(')[0]}; {hint}")]


def test_wrong_argument_count_reports_pie_s2104() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(email, email)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid arguments for function lower: expected 1, got 2",
        )
    ]


def test_wrong_argument_type_reports_pie_s2104() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(count)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        )
    ]


def test_unknown_argument_suppresses_call_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(missing)\n"
        )
    )
    expression = _call(result)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN
    assert (
        result.model.expression_value_types[expression.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


def test_call_diagnostic_uses_call_span() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = normalize(email)\n",
        path="functions.pietto",
    )
    result = analyze(script)
    expression = _call(result)
    diagnostic = result.diagnostics[0]

    assert diagnostic.code == "PIE-S2103"
    assert diagnostic.location.path == expression.span.path == "functions.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        expression.span.line,
        expression.span.column,
        expression.span.end_line,
        expression.span.end_column,
    )


def test_function_typing_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(email)\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_q1_closed_builtin_catalog_has_typed_nullable_results() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    name: Text | None\n"
            "    amount: Decimal | None\n"
            "    count: Int | None\n"
            "    happened_at: Timestamp | None\n"
            'source users: User = postgres.table("users")\n'
            "table projected:\n"
            "    from users\n"
            "    select:\n"
            '        normalized = replace(upper(name), "A", "a")\n'
            "        fragment = substr(name, 1, 2)\n"
            '        present = contains(name, "a")\n'
            "        magnitude = abs(amount)\n"
            "        direction = sign(count)\n"
            "        day_number = day(happened_at)\n"
            "        civil_date = date_of(happened_at)\n"
        )
    )
    table = _table(result)
    types = tuple(
        result.model.expression_value_types[item.expression]
        for item in table.select_items
    )

    assert result.diagnostics == ()
    assert tuple(value_type.resolved_type.name for value_type in types) == (
        "Text",
        "Text",
        "Bool",
        "Decimal",
        "Int",
        "Int",
        "Date",
    )
    assert all(
        value_type.nullability is EffectiveNullability.NULLABLE for value_type in types
    )


def test_abs_keeps_its_argument_type_and_nullability() -> None:
    # A null argument is read as a Decimal.
    result = analyze(
        _parse(
            "type Age = Int\n"
            "shape User:\n"
            "    count: Int\n"
            "    score: Float | None\n"
            "    age: Age\n"
            "    amount: Decimal | None\n"
            "    name: Text\n"
            'source users: User = postgres.table("users")\n'
            "table projected:\n"
            "    from users\n"
            "    where abs(count)\n"
            "    select:\n"
            "        a = abs(count)\n"
            "        b = abs(score)\n"
            "        c = abs(age)\n"
            "        d = abs(-1.5)\n"
            "        e = abs(amount)\n"
            "        f = abs(None)\n"
            "        g = abs(name)\n"
        )
    )
    table = _table(result)
    types = tuple(
        result.model.expression_value_types[item.expression]
        for item in table.select_items
    )

    assert [(t.resolved_type.name, t.nullability.value) for t in types[:6]] == [
        ("Int", "non_null"),
        ("Float", "nullable"),
        ("Int", "non_null"),
        ("Float", "non_null"),
        ("Decimal", "nullable"),
        ("Decimal", "nullable"),
    ]
    assert types[6].kind is ValueTypeKind.UNKNOWN
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        ("PIE-S2202", "Expected Bool expression in where clause", 11, 11),
        (
            "PIE-S2104",
            "Invalid argument type for function abs at position 1: "
            "expected Int, Float or Decimal, got Text",
            19,
            13,
        ),
    ]

    # No signature fixes its type beside an argument of unknown type, such as
    # a field of a source without a shape; as a condition it is a number.
    result = analyze(
        _parse(
            'source items = postgres.table("items")\n'
            "table projected:\n"
            "    from items\n"
            "    where abs(t)\n"
            "    select:\n"
            "        a = abs(t) * 2\n"
            "        b = abs(t) in (1.5, 2.5)\n"
        )
    )
    product, membership = (item.expression for item in _table(result).select_items)
    assert isinstance(product, BinaryExpr)
    assert isinstance(membership, MembershipExpr)

    assert [
        result.model.expression_value_types[call].kind
        for call in (product.left, membership.value)
    ] == [ValueTypeKind.UNKNOWN, ValueTypeKind.UNKNOWN]
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-S2303",
            "Source items has no bound shape; row schema is unknown",
            1,
            1,
        ),
        ("PIE-S2202", "Expected Bool expression in where clause", 4, 11),
    ]


def test_function_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(trim(email))\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["projected"]
    assert isinstance(definition, TableDef)
    return definition


def _where_expression(result: SemanticResult) -> Expression:
    table = _table(result)
    assert table.where_clause is not None
    return table.where_clause.expression


def _call(result: SemanticResult) -> CallExpr:
    expression = _table(result).select_items[0].expression
    assert isinstance(expression, CallExpr)
    return expression


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
