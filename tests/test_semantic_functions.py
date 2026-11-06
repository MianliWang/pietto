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


def test_scalar_functions_keep_their_approved_types() -> None:
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


# string_agg takes two Text row expressions and orders them by its own keys.
@pytest.mark.parametrize(
    ("call", "expected"),
    (
        ('string_agg(None, ",", order by count)', "expected two Text arguments"),
        ("string_agg(email, None, order by count)", "expected two Text arguments"),
        ('string_agg(nothing, ",", order by count)', "expected two Text arguments"),
        ("string_agg(email, nothing, order by count)", "expected two Text arguments"),
        (
            'string_agg(coalesce(None, None), ",", order by count)',
            "expected two Text arguments",
        ),
        (
            "string_agg(email, coalesce(nothing, None), order by count)",
            "expected two Text arguments",
        ),
        ('string_agg(None + None, ",", order by count)', "expected two Text arguments"),
        ('string_agg(-nothing, ",", order by count)', "expected two Text arguments"),
        # A condition is no value of the conditional.
        (
            'string_agg(None if count > 1 else None, ",", order by count)',
            "expected two Text arguments",
        ),
        (
            "string_agg(email, coalesce(nothing if True else None), order by count)",
            "expected two Text arguments",
        ),
        ('string_agg(email, ",")', "expected ORDER BY key"),
    ),
)
def test_string_agg_refuses_a_null_argument_and_a_missing_order(
    call: str, expected: str
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    let nothing = None\n"
            "    select:\n"
            f"        summary = {call}\n",
            path="main.pietto",
        )
    )

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            f"Invalid arguments for aggregate string_agg: {expected}",
            9,
            19,
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


_AGGREGATES = (
    "the available aggregates are avg, count, count_distinct, max, median, min, "
    "quantile, stddev, string_agg and sum"
)
_QUANTILE = (
    "write `quantile(x, q)`, the interpolated quantile (pandas `Series.quantile`) "
    "with q a Float literal from 0.0 to 1.0; "
)
_SAMPLE = "write `stddev`, the sample standard deviation (Python `statistics.stdev`)"
_POPULATION = (
    "`stddev` is the sample standard deviation (Python `statistics.stdev`); "
    "MySQL `STD`/`STDDEV` and numpy `std` are the population deviation, which "
    "is not available"
)
_COLLECT = (
    "a Collect read is the select item `name = collect relation` in an "
    "EXPLICIT_MODULES project"
)
_NOW = "write `now()`, the UTC time when the query runs"


@pytest.mark.parametrize(
    ("call", "hint"),
    [
        ("length(email)", "use `len(Text)` instead"),
        ("char_length(email)", "use `len(Text)` instead"),
        (
            "generate_series(1, 3, 1)",
            "it is a table function, read with `from generate_series(start, stop, "
            "step) as n` in an EXPLICIT_MODULES project",
        ),
        ("variance(count)", _AGGREGATES),
        ("mean(count)", _AGGREGATES),
        # Lane F: the sample spellings name `stddev`; the population ones say
        # why they are not available, also where a capital makes `STDDEV`.
        ("stdev(count)", _SAMPLE),
        ("stddev_samp(count)", _SAMPLE),
        ("statistics.stdev(count)", _SAMPLE),
        ("std(count)", _POPULATION),
        ("pstdev(count)", _POPULATION),
        ("stddev_pop(count)", _POPULATION),
        ("statistics.pstdev(count)", _POPULATION),
        ("STDDEV(count)", _POPULATION),
        ("Stddev(count)", _POPULATION),
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
        ("QUANTILE(count, 0.5)", _AGGREGATES),
        # The SQL and numpy percentile spellings name `quantile`.
        *(
            (f"{name}(count)", _QUANTILE + "`median(x)` is `quantile(x, 0.5)`")
            for name in (
                "percentile",
                "percentile_approx",
                "PERCENTILE_CONT",
                "approx_percentile",
            )
        ),
        (
            "percentile_disc(count)",
            _QUANTILE + "a discrete percentile that picks one value is not available",
        ),
        # Lowercase `concat` is a builtin.
        ('CONCAT(email, "!")', "write `concat(...)` in lowercase"),
        ("Concat(email, email)", "write `concat(...)` in lowercase"),
        # SQL's GREATEST and LEAST skip a NULL; `max(a, b)` and `min(a, b)` do not.
        (
            "greatest(count, count)",
            "write `max(a, b)`, which is None when either value is None",
        ),
        (
            "LEAST(count, count)",
            "write `min(a, b)`, which is None when either value is None",
        ),
        # Phase72: the range spellings are comparison chains.
        (
            "in_range(count, count, count)",
            "write the half-open range `a <= ts < b`",
        ),
        (
            "ranges_overlap(count, count, count, count)",
            "write `a_start < b_stop and b_start < a_stop`",
        ),
        # The UTC time of the running query is `now()`, its date
        # `date_of(now())`; lowercase `now` is a builtin.
        ("current_timestamp()", _NOW),
        ("CURRENT_TIMESTAMP()", _NOW),
        ("utcnow()", _NOW),
        ("utc_now()", _NOW),
        ("datetime.now()", _NOW),
        ("datetime.utcnow()", _NOW),
        ("today()", "write `date_of(now())`, the UTC date when the query runs"),
        ("date.today()", "write `date_of(now())`, the UTC date when the query runs"),
        ("NOW()", "write `now()` in lowercase"),
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


_EVENTS = (
    "shape Event:\n"
    "    id: Int\n"
    "    k: Int\n"
    "    start: Timestamp\n"
    "    stop: Timestamp | None\n"
    'source events: Event = postgres.table("events")\n'
)


def test_now_is_a_never_none_timestamp_in_select_items_and_where() -> None:
    """`now()` is the UTC Timestamp of the running query, never None; a
    WHERE reads it in a comparison chain and `date_of(now())` is its date."""
    result = analyze(
        _parse(
            _EVENTS + "table projected:\n"
            "    from events\n"
            "    where start <= now() < stop\n"
            "    select:\n"
            "        seen = now()\n"
            "        day = date_of(now())\n"
        )
    )

    assert result.diagnostics == ()
    seen, day = (item.expression for item in _table(result).select_items)
    types = result.model.expression_value_types
    assert (types[seen].resolved_type.name, types[seen].nullability) == (
        "Timestamp",
        EffectiveNullability.NON_NULL,
    )
    assert (types[day].resolved_type.name, types[day].nullability) == (
        "Date",
        EffectiveNullability.NON_NULL,
    )


def test_now_takes_no_argument() -> None:
    result = analyze(
        _parse(
            _EVENTS + "table projected:\n"
            "    from events\n"
            "    select:\n"
            "        seen = now(start)\n"
        )
    )

    assert [(d.code, d.message) for d in result.diagnostics] == [
        ("PIE-S2104", "Invalid arguments for function now: expected 0, got 1")
    ]


_NOW_ONLY = "`now()` is available only in a SELECT item or a WHERE comparison"


@pytest.mark.parametrize(
    ("body", "column", "message"),
    [
        (
            "    let d = date_of(now())\n    group by d\n    select:\n        d = d\n",
            21,
            "`now()` cannot be in a GROUP BY key: every row has the same `now()`, "
            "so it never splits a group",
        ),
        (
            "    select:\n        id = id\n    order by now()\n",
            14,
            "`now()` cannot be in an ORDER BY key: every row has the same "
            "`now()`; order by a field",
        ),
        (
            "    let o = events\n    inner join o on o.start < now()\n"
            "    select:\n        id = id\n",
            31,
            "`now()` cannot be in a JOIN condition; compare it in WHERE",
        ),
        (
            "    select:\n        id = id\n        t = now()\n    order by t\n",
            13,
            "`now()` cannot be in an ORDER BY key: every row has the same "
            "`now()`; order by a field",
        ),
        ("    let t = now()\n    select:\n        t = t\n", 13, _NOW_ONLY),
        (
            "    group by k\n    select:\n        k = k\n        n = count()\n"
            "    having max(start) < now()\n",
            25,
            _NOW_ONLY,
        ),
        (
            "    select:\n        id = id\n"
            "        w = row_number() window(order by now())\n",
            42,
            _NOW_ONLY,
        ),
        (
            "    select:\n        id = id\n"
            "        w = row_number() window(order by id)\n    qualify start < now()\n",
            21,
            _NOW_ONLY,
        ),
    ],
    ids=[
        "group_key",
        "order_key",
        "join",
        "order_key_alias",
        "let",
        "having",
        "window",
        "qualify",
    ],
)
def test_now_outside_select_items_and_where_is_refused_where_it_stands(
    body: str, column: int, message: str
) -> None:
    lines = (_EVENTS + "table projected:\n    from events\n" + body).splitlines()
    line = next(n for n, text in enumerate(lines, 1) if "now()" in text)
    result = analyze(_parse("\n".join(lines) + "\n"))

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == [("PIE-S2387", line, column, message)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "def stamp() -> Timestamp: return now()\n",
            _NOW_ONLY,
        ),
        (
            "shape Stamped:\n    stamp: Timestamp derive now()\n",
            "`now()` cannot be in a field derive, which reads one stored row; "
            "select `now()` in a query",
        ),
    ],
    ids=["def_body", "field_derive"],
)
def test_now_outside_a_relation_is_refused_where_it_stands(
    source: str, message: str
) -> None:
    result = analyze(_parse(source))

    assert [(d.code, d.message) for d in result.diagnostics] == [("PIE-S2387", message)]


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


_SAME_VALUE_SOURCE = (
    "enum Status: open, closed\n"
    "type Code = Text\n"
    "shape Item:\n"
    "    id: Int\n"
    "    owner_id: Int | None\n"
    "    count: Int\n"
    "    amount: Decimal | None\n"
    "    ratio: Float | None\n"
    "    code: Code\n"
    "    note: Text | None\n"
    "    opened_on: Date | None\n"
    "    status: Status | None\n"
    "    pk = unique(id)\n"
    'source items: Item = postgres.table("items")\n'
    "shape Tag:\n"
    "    id: Int\n"
    "    item_id: Int | None\n"
    "    pk = unique(id)\n"
    'source tags: Tag = postgres.table("tags")\n'
)


def test_same_value_is_a_bool_that_is_never_none() -> None:
    # Each cell of the operands' nullability gives a non-null Bool, and the
    # operands compare as for `==`.
    result = analyze(
        _parse(
            _SAME_VALUE_SOURCE + "table projected:\n"
            "    from items\n"
            "    where same_value(owner_id, count)\n"
            "    select:\n"
            "        both_values = same_value(count, id)\n"
            "        left_null = same_value(owner_id, count)\n"
            "        right_null = same_value(count, owner_id)\n"
            "        both_null = same_value(owner_id, owner_id)\n"
            "        numbers = same_value(amount, ratio)\n"
            '        texts = same_value(code, "x")\n'
            '        day = same_value(opened_on, "2024-01-02")\n'
            '        label = same_value(status, "open")\n'
            "        typed_null = same_value(count + None, owner_id)\n"
        )
    )
    table = _table(result)
    types = tuple(
        result.model.expression_value_types[expression]
        for expression in (
            *(item.expression for item in table.select_items),
            _where_expression(result),
        )
    )

    assert result.diagnostics == ()
    assert {
        (value_type.resolved_type.name, value_type.nullability) for value_type in types
    } == {("Bool", EffectiveNullability.NON_NULL)}


def test_same_value_in_join_on_matches_no_key() -> None:
    # NULL-safe equality may match many rows of a unique key that admits NULL,
    # so it is no key match and an aggregate over the JOIN is refused.
    def check(predicate: str) -> list[tuple[str, int]]:
        result = analyze(
            _parse(
                _SAME_VALUE_SOURCE + "query joined:\n"
                "    from items\n"
                "    let tag = tags\n"
                f"    left join tag on {predicate}\n"
                "    group by items.id\n"
                "    select:\n"
                "        id = items.id\n"
                "        total = sum(items.count)\n"
            )
        )
        return [(item.code, item.location.line) for item in result.diagnostics]

    assert check("tag.id == items.owner_id") == []
    assert check("same_value(tag.id, items.owner_id)") == [("PIE-S2381", 27)]


def test_same_value_in_where_does_not_reject_unmatched_left_join_rows() -> None:
    # `same_value(tag.item_id, items.owner_id)` is True for an unmatched row
    # whose `owner_id` is None, so WHERE keeps it, as `==` would not.
    def warnings(predicate: str) -> list[str]:
        result = analyze(
            _parse(
                _SAME_VALUE_SOURCE + "query joined:\n"
                "    from items\n"
                "    let tag = tags\n"
                "    left join tag on tag.item_id == items.id\n"
                f"    where {predicate}\n"
                "    select:\n"
                "        id = items.id\n"
            )
        )
        return [item.code for item in result.diagnostics]

    assert warnings("tag.id == items.owner_id") == ["PIE-S2383"]
    assert warnings("same_value(tag.id, items.owner_id)") == []


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            "same_value(owner_id, None)",
            "Invalid argument type for function same_value at position 2: "
            "expected a non-None value, got None; write `x is None` instead",
        ),
        (
            "same_value(nothing, count)",
            "Invalid argument type for function same_value at position 1: "
            "expected a non-None value, got None; write `x is None` instead",
        ),
        (
            "same_value(None, None)",
            "Invalid argument type for function same_value at position 1: "
            "expected a non-None value, got None",
        ),
        (
            "same_value(count)",
            "Invalid arguments for function same_value: expected 2, got 1",
        ),
        (
            "same_value(count, count, count)",
            "Invalid arguments for function same_value: expected 2, got 3",
        ),
        (
            "same_value(count, code)",
            "Invalid argument types for function same_value: "
            "expected comparable operands",
        ),
        (
            "same_value(opened_on, count)",
            "Invalid argument types for function same_value: "
            "expected comparable operands",
        ),
        (
            'same_value(status, "gone")',
            "Invalid argument types for function same_value: "
            "expected comparable operands",
        ),
        (
            "same_value(amount / 2, code)",
            "Invalid argument types for function same_value: "
            "expected comparable operands",
        ),
    ],
)
def test_same_value_refuses_none_and_operands_that_do_not_compare(
    call: str, message: str
) -> None:
    result = analyze(
        _parse(
            _SAME_VALUE_SOURCE + "table projected:\n"
            "    from items\n"
            "    let nothing = None\n"
            "    select:\n"
            f"        value = {call}\n",
            path="main.pietto",
        )
    )

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-S2104", message, 24, 17)]
    # Operands that `same_value` refuses for their types, `==` refuses too.
    if "comparable" in message:
        operands = call.removeprefix("same_value(").removesuffix(")")
        compared = analyze(
            _parse(
                _SAME_VALUE_SOURCE
                + "table projected:\n"
                "    from items\n"
                "    select:\n"
                "        value = {} == {}\n".format(*operands.split(", "))
            )
        )
        assert [item.code for item in compared.diagnostics] == ["PIE-S2105"]


def test_same_value_refuses_none_reaching_it_through_a_def_argument() -> None:
    result = analyze(
        _parse(
            _SAME_VALUE_SOURCE + "def eqs(x: Int | None, y: Int | None) -> Bool:\n"
            "    return same_value(x, y)\n"
            "table projected:\n"
            "    from items\n"
            "    select:\n"
            "        value = eqs(None, count)\n",
            path="main.pietto",
        )
    )

    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-S2104",
            "Invalid argument type for function same_value at position 1: "
            "expected a non-None value, got None; write `x is None` instead",
        )
    ]


_CONCAT_SOURCE = (
    "type Label = Text\n"
    "shape Item:\n"
    "    code: Text\n"
    "    note: Text | None\n"
    "    tag: Label\n"
    "    qty: Int\n"
    "    amount: Decimal\n"
    'source items: Item = postgres.table("items")\n'
    "table projected:\n"
    "    from items\n"
    "    select:\n"
)


def test_concat_joins_text_and_is_null_when_any_argument_is() -> None:
    result = analyze(
        _parse(
            _CONCAT_SOURCE + '        pair = concat(code, "-")\n'
            "        triple = concat(code, note, tag)\n"
            "        nulled = concat(code, None)\n"
            '        framed = concat("[", tag, "]")\n'
        )
    )
    table = _table(result)
    types = tuple(
        result.model.expression_value_types[item.expression]
        for item in table.select_items
    )

    assert result.diagnostics == ()
    assert {value_type.resolved_type.name for value_type in types} == {"Text"}
    assert tuple(value_type.nullability for value_type in types) == (
        EffectiveNullability.NON_NULL,
        EffectiveNullability.NULLABLE,
        EffectiveNullability.NULLABLE,
        EffectiveNullability.NON_NULL,
    )
    # A None argument is read as a Text, as for the other Text builtins.
    null_argument = table.select_items[2].expression
    assert isinstance(null_argument, CallExpr)
    assert (
        result.model.expression_value_types[
            null_argument.arguments[1]
        ].resolved_type.name
        == "Text"
    )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            "concat(code)",
            "Invalid arguments for function concat: expected at least 2, got 1",
        ),
        (
            "concat()",
            "Invalid arguments for function concat: expected at least 2, got 0",
        ),
        (
            "concat(code, qty)",
            "Invalid argument type for function concat at position 2: "
            "expected Text, got Int",
        ),
        (
            "concat(code, tag, True)",
            "Invalid argument type for function concat at position 3: "
            "expected Text, got Bool",
        ),
        (
            "concat(code, amount / 2)",
            "Invalid argument type for function concat at position 2: "
            "expected Text, got numeric",
        ),
    ],
)
def test_concat_refuses_one_argument_and_a_non_text_argument(
    call: str, message: str
) -> None:
    result = analyze(_parse(_CONCAT_SOURCE + f"        value = {call}\n"))

    assert [(d.code, d.message) for d in result.diagnostics] == [("PIE-S2104", message)]


_PAD_SOURCE = (
    "type Label = Text\n"
    "shape Item:\n"
    "    code: Text\n"
    "    note: Text | None\n"
    "    tag: Label\n"
    "    qty: Int\n"
    "    due: Date | None\n"
    "    at: Timestamp\n"
    'source items: Item = postgres.table("items")\n'
    "table projected:\n"
    "    from items\n"
    "    select:\n"
)


def test_lpad_and_add_months_keep_their_types_and_none() -> None:
    result = analyze(
        _parse(
            _PAD_SOURCE + '        padded = lpad(code, 5, "0")\n'
            '        tagged = lpad(tag, qty, " ")\n'
            '        noted = lpad(note, 3, "雪")\n'
            '        nulled = lpad(None, 3, "x")\n'
            "        later = add_months(due, 1)\n"
            "        stamped = add_months(date_of(at), qty)\n"
            "        unset = add_months(None, 1)\n"
        )
    )
    types = tuple(
        result.model.expression_value_types[item.expression]
        for item in _table(result).select_items
    )

    assert result.diagnostics == ()
    assert tuple(
        (value_type.resolved_type.name, value_type.nullability) for value_type in types
    ) == (
        ("Text", EffectiveNullability.NON_NULL),
        ("Text", EffectiveNullability.NON_NULL),
        ("Text", EffectiveNullability.NULLABLE),
        ("Text", EffectiveNullability.NULLABLE),
        ("Date", EffectiveNullability.NULLABLE),
        ("Date", EffectiveNullability.NON_NULL),
        ("Date", EffectiveNullability.NULLABLE),
    )


_FILL = 'fill must be a one-character Text literal, such as "0"'
_RJUST = (
    "write `lpad(s, width, fill)`, which pads like Python `str.rjust` and never "
    "truncates"
)


@pytest.mark.parametrize(
    ("call", "code", "message"),
    [
        (
            "lpad(code, 5)",
            "PIE-S2104",
            f"Invalid arguments for function lpad: expected 3, got 2; {_FILL}",
        ),
        *(
            (
                f"lpad(code, 5, {fill})",
                "PIE-S2104",
                f"Invalid arguments for function lpad: {_FILL}",
            )
            for fill in ('"00"', '""', "None", "note", "tag")
        ),
        (
            "lpad(code, 5, 0)",
            "PIE-S2104",
            "Invalid argument type for function lpad at position 3: "
            "expected Text, got Int",
        ),
        ('rjust(code, 5, "0")', "PIE-S2103", f"Unknown function: rjust; {_RJUST}"),
        ('code.rjust(5, "0")', "PIE-S2103", f"Unknown function: code.rjust; {_RJUST}"),
        (
            "add_months(at, 1)",
            "PIE-S2104",
            "Invalid argument type for function add_months at position 1: "
            "expected Date, got Timestamp; add_months takes a Date, such as "
            "add_months(date_of(ts), n)",
        ),
        (
            'add_months(due, "1")',
            "PIE-S2104",
            "Invalid argument type for function add_months at position 2: "
            "expected Int, got Text",
        ),
    ],
)
def test_lpad_and_add_months_refuse_their_variants(
    call: str, code: str, message: str
) -> None:
    result = analyze(_parse(_PAD_SOURCE + f"        value = {call}\n"))

    assert [(d.code, d.message) for d in result.diagnostics] == [(code, message)]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "    select:\n        v = not concat(t, u)\n",
            ("PIE-S2105", "Invalid operands for operator not: expected Bool operand"),
        ),
        (
            "    where concat(t, u)\n    select:\n        t\n",
            ("PIE-S2202", "Expected Bool expression in where clause"),
        ),
    ],
)
def test_concat_is_text_in_a_condition_over_a_row_of_unknown_type(
    body: str, expected: tuple[str, str]
) -> None:
    result = analyze(
        _parse(
            'source items = postgres.table("items")\nquery q:\n    from items\n' + body
        )
    )

    assert [
        (d.code, d.message) for d in result.diagnostics if d.severity is Severity.ERROR
    ] == [expected]


_EXTREMA_SOURCE = (
    "shape Item:\n"
    "    a: Int\n"
    "    b: Int | None\n"
    "    x: Float\n"
    "    t: Text\n"
    "    u: Text | None\n"
    "    d: Date\n"
    "    ts: Timestamp\n"
    "    ts2: Timestamp | None\n"
    "    uu: UUID\n"
    "    flag: Bool\n"
    'source items: Item = postgres.table("items")\n'
    "table projected:\n"
    "    from items\n"
)


def test_max_and_min_of_two_values_keep_their_type_and_are_none_when_either_is() -> (
    None
):
    result = analyze(
        _parse(
            _EXTREMA_SOURCE + "    select:\n"
            "        hi = max(a, b)\n"
            "        lo = min(a, 3)\n"
            "        tie = max(a, a)\n"
            "        word = min(t, u)\n"
            "        ratio = max(x, 1.5)\n"
            "        day = min(d, d)\n"
            "        nested = max(a, min(b, 3))\n"
            "        late = max(ts, ts2)\n"
            "        key = min(uu, uu)\n"
            "        both = max(flag, flag)\n"
            # 766 expression nodes, within the bound of 1000.
            "        five = max(a, max(a, max(a, max(a, a))))\n"
        )
    )
    types = [
        result.model.expression_value_types[item.expression]
        for item in _table(result).select_items
    ]

    assert result.diagnostics == ()
    assert [(item.resolved_type.name, item.nullability) for item in types] == [
        ("Int", EffectiveNullability.NULLABLE),
        ("Int", EffectiveNullability.NON_NULL),
        ("Int", EffectiveNullability.NON_NULL),
        ("Text", EffectiveNullability.NULLABLE),
        ("Float", EffectiveNullability.NON_NULL),
        ("Date", EffectiveNullability.NON_NULL),
        ("Int", EffectiveNullability.NULLABLE),
        ("Timestamp", EffectiveNullability.NULLABLE),
        ("UUID", EffectiveNullability.NON_NULL),
        ("Bool", EffectiveNullability.NON_NULL),
        ("Int", EffectiveNullability.NON_NULL),
    ]


_NONE_AT = (
    "Invalid argument type for function {} at position {}: expected a non-None "
    "value, got None"
)
_NOT_ONE_TYPE = (
    "Invalid argument types for function {}: expected same canonical comparable type"
)
_NEST = (
    "Aggregate function {0} expects 1 arguments, got 3; for more values, nest "
    "two-argument calls: {0}(a, {0}(b, c))"
)


@pytest.mark.parametrize(
    ("lets", "call", "expected"),
    [
        ("", "max(a, None)", ("PIE-S2104", _NONE_AT.format("max", 2), 17)),
        ("", "min(None, a)", ("PIE-S2104", _NONE_AT.format("min", 1), 17)),
        (
            "    let k = None\n",
            "max(a, k)",
            ("PIE-S2104", _NONE_AT.format("max", 2), 17),
        ),
        ("", "max(t, 1)", ("PIE-S2104", _NOT_ONE_TYPE.format("max"), 17)),
        ("", "min(a, 1.5)", ("PIE-S2104", _NOT_ONE_TYPE.format("min"), 17)),
        ("", "max(a, max(t, a))", ("PIE-S2104", _NOT_ONE_TYPE.format("max"), 24)),
        # An argument's own error is reported once, at the argument.
        ("", "max(nosuch, 1)", ("PIE-S2102", "Unknown field: nosuch", 21)),
        ("", "max(a, b, 1)", ("PIE-S2309", _NEST.format("max"), 17)),
        ("", "min(a, None, None)", ("PIE-S2309", _NEST.format("min"), 17)),
        # Each call writes its arguments out again, so a nest is bounded as a
        # def's expansion is.
        (
            "",
            "max(a, max(a, max(a, max(a, max(a, a)))))",
            (
                "PIE-S2399",
                "The expansion of max has 3070 expression nodes nested 16 deep; "
                "an expansion, with its arguments, has at most 1000 nodes nested "
                "at most 64 deep",
                17,
            ),
        ),
    ],
)
def test_max_and_min_refuse_none_values_that_do_not_compare_and_more_arguments(
    lets: str, call: str, expected: tuple[str, str, int]
) -> None:
    result = analyze(
        _parse(_EXTREMA_SOURCE + lets + f"    select:\n        value = {call}\n")
    )
    code, message, column = expected

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
        if d.severity is Severity.ERROR
    ] == [(code, message, 16 + bool(lets), column)]


@pytest.mark.parametrize(
    ("body", "call", "expected"),
    [
        ("max(x, y)", "bigger(a, None)", ("PIE-S2104", _NONE_AT.format("max", 2), 17)),
        ("min(y, x)", "bigger(a, None)", ("PIE-S2104", _NONE_AT.format("min", 1), 17)),
        (
            "max(x + 1, y)",
            "bigger(a, None)",
            ("PIE-S2104", _NONE_AT.format("max", 2), 17),
        ),
        (
            "max(x, y)",
            "bigger(a, bigger(a, None))",
            ("PIE-S2104", _NONE_AT.format("max", 2), 27),
        ),
        # The def reports an argument that does not fit its parameter.
        (
            "max(x, y)",
            "bigger(a, t)",
            (
                "PIE-S2395",
                "Invalid argument for def bigger at position 2 (y): expected "
                "Int | None, got Text",
                17,
            ),
        ),
        # A hand-written conditional reports its own comparison.
        (
            "y if x < y else x",
            "bigger(a, None)",
            (
                "PIE-S2105",
                "Invalid operands for operator <: comparison with null is never true",
                17,
            ),
        ),
    ],
)
def test_a_none_that_reaches_max_or_min_through_a_def_is_reported_at_the_def_call(
    body: str, call: str, expected: tuple[str, str, int]
) -> None:
    result = analyze(
        _parse(
            "def bigger(x: Int, y: Int | None) -> Int | None: return "
            + body
            + "\n"
            + _EXTREMA_SOURCE
            + f"    select:\n        value = {call}\n"
        )
    )
    code, message, column = expected

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
        if d.severity is Severity.ERROR
    ] == [(code, message, 17, column)]


def test_a_same_file_callable_named_max_or_min_keeps_the_meaning_it_had() -> None:
    """A constraint, derive or relationship named `max` leaves a two-argument
    `max` call to the aggregate's arity check, as before; a `def` of the name
    is refused as before."""

    shadowed = analyze(
        _parse(
            "constraint max(value: Int, other: Int) -> Bool: return value > other\n"
            + _EXTREMA_SOURCE
            + "    select:\n        value = max(a, a)\n"
        )
    )
    defined = analyze(
        _parse(
            "def min(x: Int, y: Int) -> Int: return x if x < y else y\n"
            + _EXTREMA_SOURCE
            + "    select:\n        value = min(a, a)\n"
        )
    )

    assert [(d.code, d.message) for d in shadowed.diagnostics] == [
        ("PIE-S2309", "Aggregate function max expects 1 arguments, got 2")
    ]
    assert [(d.code, d.message) for d in defined.diagnostics] == [
        (
            "PIE-S2398",
            "Def min has the name of a built-in function; a def cannot shadow one",
        )
    ]


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
