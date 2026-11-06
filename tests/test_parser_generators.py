"""Generator calls: `BODY for o in SOURCE [if TEST]` as a call's only
argument, read by a primary expression (Phase73 S02)."""

from __future__ import annotations

from typing import cast

import pytest

from pietto.ast_nodes import (
    AnyExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    GeneratorExpr,
    LiteralExpr,
    ParameterRefExpr,
    QueryDef,
    Span,
)
from pietto.parser_api import parse_source


def _select(item: str) -> CallExpr | AnyExpr:
    parsed = parse_source(
        f"query q:\n    from orders\n    group by k\n    select k, n = {item}\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    (query,) = parsed.ast.definitions
    return cast(CallExpr | AnyExpr, cast(QueryDef, query).select_items[1].expression)


def _at(start: int, end: int) -> tuple[int, int, int, int]:
    return (4, start, 4, end)


def _where(span: Span) -> tuple[int, int, int | None, int | None]:
    return (span.line, span.column, span.end_line, span.end_column)


def test_a_generator_is_the_only_argument_of_its_call() -> None:
    call = _select("sum(o.amount for o in group if o.paid and k > 1)")

    assert type(call) is CallExpr
    (generator,) = call.arguments
    assert type(generator) is GeneratorExpr
    assert (generator.binding_name, generator.source) == ("o", ("group",))
    assert type(generator.body) is DottedNameExpr
    assert generator.body.parts == ("o", "amount")
    assert generator.condition is not None
    assert generator.operands == (generator.body, generator.condition)
    assert _where(call.span) == _at(19, 67)
    assert _where(generator.span) == _at(23, 66)
    assert _where(generator.binding_span) == _at(36, 37)
    assert _where(generator.source_span) == _at(41, 46)


def test_a_generator_without_if_and_over_a_dotted_source_parses() -> None:
    call = _select("sum(1 for o in c.items)")

    assert type(call) is CallExpr
    (generator,) = call.arguments
    assert type(generator) is GeneratorExpr
    assert generator.source == ("c", "items")
    assert type(generator.body) is LiteralExpr and generator.condition is None
    assert generator.operands == (generator.body,)


def test_relation_any_keeps_its_own_node_and_a_test_makes_it_a_generator() -> None:
    relation = _select("any(o.paid for o in orders)")
    tested = _select("any(o.paid for o in orders if o.id > 1)")

    assert type(relation) is AnyExpr and relation.relation_name == "orders"
    assert type(tested) is CallExpr
    assert type(tested.arguments[0]) is GeneratorExpr


def test_a_generator_binder_hides_a_header_parameter_of_its_name() -> None:
    parsed = parse_source(
        "query q(o: Int, p: Int):\n    from orders\n    group by k\n"
        "    select k, n = sum(1 for o in group if o.v > p)\n"
    )
    assert parsed.ast is not None
    query = cast(QueryDef, parsed.ast.definitions[0])
    call = cast(CallExpr, query.select_items[1].expression)
    generator = cast(GeneratorExpr, call.arguments[0])

    condition = generator.condition
    assert type(condition) is ComparisonExpr
    left, right = condition.left, condition.right
    assert type(left) is DottedNameExpr and left.parts == ("o", "v")
    assert type(right) is ParameterRefExpr and right.name == "p"


@pytest.mark.parametrize(
    ("item", "message"),
    [
        (
            "sum(1 for o in group for p in group)",
            (4, 40, "Unexpected 'for'; expected ')'."),
        ),
        (
            "sum(1 for o in group if o.a if o.b)",
            (4, 47, "Missing ')' before 'if'."),
        ),
        ("sum(x for o in group, 0)", (4, 39, "Missing ')' before ','.")),
        (
            "len([o for o in group])",
            (4, 23, "Unexpected '['; expected an expression or ')'."),
        ),
    ],
)
def test_a_second_for_or_if_and_a_second_argument_stay_parse_errors(
    item: str, message: tuple[int, int, str]
) -> None:
    parsed = parse_source(
        f"query q:\n    from orders\n    group by k\n    select k, n = {item}\n"
    )

    assert parsed.ast is None
    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in parsed.diagnostics
    ] == [("PIE-P1000", *message)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            # A window call keeps callSuffix: its generator is no call argument.
            "query q:\n    from orders\n    select:\n"
            "        r = sum(1 for o in group) window(order by id)\n",
            (
                4,
                35,
                "Unexpected 'window'; expected ',' or end of line. A window call "
                "is a whole `select:` item on a line of its own.",
            ),
        ),
        (
            "query q:\n    from generate_series(1 for o in group) as n\n    select n\n",
            (2, 28, "Unexpected 'for'; expected ')' or ','."),
        ),
        (
            "query q:\n    from orders\n    select id\n"
            "    qualify sum(1 for o in group) window(order by id) > 1\n",
            (4, 19, "Unexpected 'for'."),
        ),
    ],
)
def test_window_table_function_and_qualify_calls_take_no_generator(
    source: str, message: tuple[int, int, str]
) -> None:
    parsed = parse_source(source)

    assert parsed.ast is None
    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in parsed.diagnostics
    ] == [("PIE-P1000", *message)]
