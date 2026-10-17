"""Pure inline ``def`` functions: definition checks, call checks and inlining.

A call is replaced by the def body with each argument in place of its
parameter before any call site is typed. SQL byte identity lives with the SQL
owners; project checks live with the project owners.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, is_dataclass
from typing import Any, cast

import pytest

from pietto._inline_argument import InlinedArgument
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    FunctionDef,
    NameExpr,
    SelectItem,
    Span,
    TableDef,
    inlined_arguments,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.inline_functions import inline_functions

SHAPES = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    n: Int nullable\n"
    "    text: Text not null\n"
    "    note: Text nullable\n"
    "    amount: Decimal(9, 2) not null\n"
    'source rows: Row is postgres.table("rows")\n'
)
DEFS = (
    "def pos(x: Int not null) -> Bool nullable: return x > 0\n"
    "def up(t: Text not null) -> Text not null: return upper(t)\n"
)
# The first line of a relation written after SHAPES and DEFS.
BODY_LINE = 10
SCALARS = "Bool, Int, Float, Decimal, Text, Date, Timestamp or UUID, without arguments"


def _errors(source: str) -> list[tuple[str, int, int, str]]:
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    return [
        (d.code, d.location.line, d.location.column, d.message)
        for d in analyze(parsed.ast).diagnostics
    ]


DEFINITION_ERRORS = {
    "direct_recursion": (
        "def f(x: Int not null) -> Int nullable: return f(x) + 1\n",
        [("PIE-S2396", 1, 1, "Recursive def calls are not available: f -> f")],
    ),
    "mutual_recursion_one_error_per_group": (
        "def f(x: Int not null) -> Int nullable: return g(x)\n"
        "def g(x: Int not null) -> Int nullable: return h(x) + f(x)\n"
        "def h(x: Int not null) -> Int nullable: return x\n"
        "def c(x: Int not null) -> Int nullable: return c(x)\n",
        [
            ("PIE-S2396", 1, 1, "Recursive def calls are not available: f -> g -> f"),
            ("PIE-S2396", 4, 1, "Recursive def calls are not available: c -> c"),
        ],
    ),
    "row_typed_parameter": (
        "shape Row:\n    id: Int not null\n"
        "def f(r: Row not null, x: Int not null) -> Int not null: return x\n",
        [
            (
                "PIE-S2397",
                3,
                7,
                "Def f parameter r is not used in its body; "
                "every parameter must be used",
            ),
            (
                "PIE-S2397",
                3,
                10,
                "Def f parameter r has row type Row; row-typed "
                "def parameters and results are not available yet",
            ),
        ],
    ),
    "row_typed_result": (
        "shape Row:\n    id: Int not null\n"
        "def f(x: Int not null) -> Row not null: return x\n",
        [
            (
                "PIE-S2397",
                3,
                27,
                "Def f result has row type Row; row-typed def "
                "parameters and results are not available yet",
            )
        ],
    ),
    "alias_enum_any_and_type_arguments": (
        "type Percent = Int not null\nenum Status: a, b\n"
        "def f(p: Percent not null, s: Status not null, a: Any not null, "
        "d: Decimal(9, 2) not null) -> Bool not null: "
        "return p is null and s is null and a is null and d is null\n",
        [
            (
                "PIE-S2397",
                3,
                10,
                f"Def f parameter p has type Percent; a def "
                f"parameter or result type is exactly {SCALARS}",
            ),
            (
                "PIE-S2397",
                3,
                31,
                f"Def f parameter s has type Status; a def "
                f"parameter or result type is exactly {SCALARS}",
            ),
            (
                "PIE-S2397",
                3,
                51,
                f"Def f parameter a has type Any; a def "
                f"parameter or result type is exactly {SCALARS}",
            ),
            (
                "PIE-S2397",
                3,
                68,
                f"Def f parameter d has type Decimal(...); a def "
                f"parameter or result type is exactly {SCALARS}",
            ),
        ],
    ),
    "unused_parameter": (
        "def f(a: Int not null, b: Int not null) -> Int not null: return a\n",
        [
            (
                "PIE-S2397",
                1,
                24,
                "Def f parameter b is not used in its body; "
                "every parameter must be used",
            )
        ],
    ),
    "aggregate_and_qualified_name": (
        "def f(a: Int not null) -> Int nullable: return sum(a) + rows.id\n",
        [
            (
                "PIE-S2397",
                1,
                48,
                "Def f body uses the aggregate sum; a def body "
                "reads only its parameters and calls scalar functions",
            ),
            (
                "PIE-S2397",
                1,
                57,
                "Def f body uses the qualified name rows.id; a "
                "def body reads only its parameters and calls scalar functions",
            ),
        ],
    ),
    "free_name": (
        "def f(a: Int not null) -> Bool nullable: return id > a\n",
        [("PIE-S2102", 1, 49, "Unknown field: id")],
    ),
    "builtin_aggregate_and_window_names": (
        "def lower(a: Text not null) -> Text not null: return a\n"
        "def count(a: Int not null) -> Int not null: return a\n"
        "def rank(a: Int not null) -> Int not null: return a\n",
        [
            (
                "PIE-S2398",
                line,
                1,
                f"Def {name} has the name of a built-in "
                "function; a def cannot shadow one",
            )
            for line, name in ((1, "lower"), (2, "count"), (3, "rank"))
        ],
    ),
    "callable_namespace_duplicates": (
        "derive d(a: Int not null) -> Int not null:\n    a\n"
        "def d(a: Int not null) -> Int not null: return a\n"
        "def f(a: Int not null, a: Int not null) -> Int nullable: return a + a\n"
        "def f(a: Int not null) -> Int not null: return a\n",
        [
            ("PIE-S2001", 3, 1, "Duplicate symbol name in callable namespace: d"),
            ("PIE-S2001", 4, 24, "Duplicate parameter name in def f: a"),
            ("PIE-S2001", 5, 1, "Duplicate symbol name in callable namespace: f"),
        ],
    ),
    "result_type": (
        "def f(a: Int not null) -> Text not null: return a\n",
        [
            (
                "PIE-S2402",
                1,
                49,
                "Def f body type Int does not match declared return type Text",
            )
        ],
    ),
    "result_nullability_is_proven": (
        "def f(a: Text nullable) -> Text not null: return lower(a)\n"
        "def g(a: Int not null) -> Bool not null: return a > 1\n"
        'def h(a: Text nullable) -> Text not null: return coalesce(a, "")\n',
        [
            (
                "PIE-S2402",
                1,
                50,
                "Def f body may be null, but its declared return type is not null",
            ),
            (
                "PIE-S2402",
                2,
                49,
                "Def g body may be null, but its declared return type is not null",
            ),
        ],
    ),
    "calls_inside_a_body": (
        "def g(t: Text not null) -> Text not null: return upper(t)\n"
        "def f(a: Text nullable) -> Text nullable: return g(a)\n"
        "def h(a: Text not null) -> Text not null: return g(a, a)\n"
        "def k(a: Text not null) -> Text not null: return frob(a)\n"
        "derive d(a: Int not null) -> Int not null:\n    a\n"
        "def m(a: Int not null) -> Int not null: return d(a)\n",
        [
            (
                "PIE-S2395",
                2,
                50,
                "Invalid argument for def g at position 1 (t): "
                "expected Text not null, got Text nullable",
            ),
            ("PIE-S2395", 3, 50, "Invalid arguments for def g: expected 1, got 2"),
            ("PIE-S2103", 4, 50, "Unknown function: frob"),
            ("PIE-S2103", 7, 48, "Unknown function: d"),
        ],
    ),
    "type_argument_call_before_its_def": (
        "def f(x: Int not null) -> Float not null: return cast(x as Float(g(1)))\n"
        "def g(x: Int not null) -> Int not null: return x\n",
        [("PIE-S2397", 1, 66, "A def call is not available in a type argument: g")],
    ),
    "type_argument_call_after_its_def": (
        "def g(x: Int not null) -> Int not null: return x\n"
        "def f(x: Int not null) -> Float not null: return cast(x as Float(g(1)))\n",
        [("PIE-S2397", 2, 66, "A def call is not available in a type argument: g")],
    ),
    "recursion_through_a_type_argument": (
        "def f(x: Int not null) -> Float not null: return cast(x as Float(f(1)))\n",
        [
            ("PIE-S2396", 1, 1, "Recursive def calls are not available: f -> f"),
            ("PIE-S2397", 1, 66, "A def call is not available in a type argument: f"),
        ],
    ),
    "parameter_in_a_type_argument": (
        "def f(x: Int not null, p: Int not null) -> Decimal not null: "
        "return cast(x as Decimal(p, 2))\n",
        [
            (
                "PIE-S2105",
                1,
                69,
                "Invalid cast: cast(Int as Decimal(..., 2)) is not supported; "
                "expected cast(Int as Float), the only supported cast",
            )
        ],
    ),
    "expansion_size": (
        "def f0(x: Int not null) -> Int nullable: return x + x\n"
        + "".join(
            f"def f{i}(x: Int not null) -> Int nullable: return "
            f"f{i - 1}(x) + f{i - 1}(x)\n"
            for i in range(1, 10)
        ),
        [
            (
                "PIE-S2399",
                9,
                49,
                "The expansion of def f8 has 1023 expression nodes "
                "nested 10 deep; an expansion, with its arguments, has at most 1000 "
                "nodes nested at most 64 deep",
            )
        ],
    ),
    "expansion_depth": (
        "def f0(x: Int not null) -> Int nullable: return x + 1\n"
        + "".join(
            f"def f{i}(x: Int not null) -> Int nullable: return f{i - 1}(x) + 1\n"
            for i in range(1, 64)
        ),
        [
            (
                "PIE-S2399",
                64,
                50,
                "The expansion of def f63 has 129 expression nodes "
                "nested 65 deep; an expansion, with its arguments, has at most 1000 "
                "nodes nested at most 64 deep",
            )
        ],
    ),
}


@pytest.mark.parametrize(
    ("source", "expected"), DEFINITION_ERRORS.values(), ids=DEFINITION_ERRORS
)
def test_each_definition_error_is_reported_at_the_def(
    source: str, expected: list[tuple[str, int, int, str]]
) -> None:
    assert _errors(source) == expected


CALL_ERRORS = {
    "where_nullability": (
        "table t:\n    from rows\n    where pos(n)\n    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got Int nullable",
            )
        ],
    ),
    "where_type_is_not_converted": (
        "table t:\n    from rows\n    where pos(amount) and pos(text)\n"
        "    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got Decimal not null",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 2,
                27,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got Text not null",
            ),
        ],
    ),
    "select_and_order_by": (
        "table t:\n    from rows\n    select:\n        id\n        u = up(id)\n"
        "    order by: up(note) asc\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 4,
                13,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got Int not null",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 5,
                15,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got Text nullable",
            ),
        ],
    ),
    "row_let": (
        "table t:\n    from rows\n    let: v = up(note)\n    select:\n"
        "        id\n        w = v\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                14,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got Text nullable",
            )
        ],
    ),
    "satisfying": (
        "table t:\n    from rows\n    group by: text\n    select:\n        text\n"
        "        m = max(n)\n    satisfying: pos(m)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 6,
                17,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got Int nullable",
            )
        ],
    ),
    "shape_check_and_field_derive": (
        "shape S:\n    a: Int nullable\n    b: Text nullable\n"
        "    c: Text not null derive up(b)\n    check k: pos(a)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 3,
                29,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got Text nullable",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 4,
                14,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got Int nullable",
            ),
        ],
    ),
    "nested_call_argument": (
        "table t:\n    from rows\n    where pos(len(up(note)))\n"
        "    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                19,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got Text nullable",
            )
        ],
    ),
    "arity": (
        "table t:\n    from rows\n    where pos(id, id)\n    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid arguments for def pos: expected 1, got 2",
            )
        ],
    ),
    "oversized_window_argument": (
        "def t2(x: Int nullable) -> Int nullable: return x + x\n"
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        t2(lag(coalesce(" + ", ".join(["n"] * 500) + ")) window:\n"
        "            order by:\n                id\n        ) > 0\n",
        [
            (
                "PIE-S2399",
                BODY_LINE + 6,
                9,
                "The expansion of def t2 has 1009 expression nodes nested 5 deep; "
                "an expansion, with its arguments, has at most 1000 nodes nested "
                "at most 64 deep",
            )
        ],
    ),
    "oversized_call_reports_once": (
        "def f(x: Int nullable) -> Int nullable: return x + x + x + x\n"
        "table t:\n    from rows\n    select:\n        id\n"
        "        v = f(f(f(f(f(f(id))))))\n",
        [
            (
                "PIE-S2399",
                BODY_LINE + 5,
                15,
                "The expansion of def f has 2047 "
                "expression nodes nested 16 deep; an expansion, with its arguments, "
                "has at most 1000 nodes nested at most 64 deep",
            )
        ],
    ),
}


@pytest.mark.parametrize(
    ("relation", "expected"), CALL_ERRORS.values(), ids=CALL_ERRORS
)
def test_each_call_is_checked_where_its_expansion_is_typed(
    relation: str, expected: list[tuple[str, int, int, str]]
) -> None:
    assert _errors(SHAPES + DEFS + relation) == expected


def test_an_alias_argument_matches_its_canonical_type() -> None:
    source = (
        "type Percent = Int not null\nshape P:\n    pct: Percent not null\n"
        'source ps: P is postgres.table("ps")\n'
        "def pos(x: Int not null) -> Bool nullable: return x > 0\n"
        "table t:\n    from ps\n    where pos(pct)\n    select:\n        pct\n"
    )
    assert _errors(source) == []


def test_keywords_name_a_def_and_its_parameter() -> None:
    source = (
        SHAPES + "def def(return: Int not null) -> Int nullable: return return + 1\n"
        "table t:\n    from rows\n    select:\n        id\n        v = def(id)\n"
    )
    assert _errors(source) == []


def _shape(value: object) -> object:
    """An AST value without its source spans."""

    if type(value) is tuple:
        return tuple(_shape(item) for item in value)
    if is_dataclass(value) and type(value).__module__ == "pietto.ast_nodes":
        return (
            type(value).__name__,
            tuple(
                (item.name, _shape(getattr(value, item.name)))
                for item in fields(value)
                if item.name != "span"
            ),
        )
    return value


def _inlined(source: str) -> Any:
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    inlined, diagnostics = inline_functions(parsed.ast)
    assert diagnostics == ()
    return inlined


def _location(span: Span) -> tuple[int, int, int, int]:
    return (span.line, span.column, span.end_line, span.end_column)


def test_a_call_becomes_its_body_with_each_argument_in_place() -> None:
    called = parse_source(
        SHAPES + "def small(v: Int not null) -> Bool nullable: return v > 0 and v < 9\n"
        "table t:\n    from rows\n    where small(id) and small(id + 1)\n"
        "    select:\n        id\n",
        path="m.pietto",
    ).ast
    written = parse_source(
        SHAPES + "table t:\n    from rows\n"
        "    where (id > 0 and id < 9) and ((id + 1) > 0 and (id + 1) < 9)\n"
        "    select:\n        id\n",
        path="m.pietto",
    ).ast
    assert called is not None and written is not None
    unchanged, none = inline_functions(written)
    assert (unchanged, none) == (written, ())
    assert unchanged is written

    inlined, diagnostics = inline_functions(called)
    assert diagnostics == ()
    assert not any(type(item) is FunctionDef for item in inlined.definitions)
    assert _shape(inlined) == _shape(written)

    # Every node keeps a real location: the body is at the call, and each use
    # of an argument is at the argument. Uses differ only in the internal span
    # occurrence, and every use carries the parameter it must fit.
    expression: Any = cast(TableDef, inlined.definitions[-1]).where_clause
    calls: Any = cast(TableDef, called.definitions[-1]).where_clause
    expression, calls = expression.expression, calls.expression
    assert type(calls) is BinaryExpr and type(calls.left) is CallExpr
    call, argument = calls.left, calls.left.arguments[0]
    first = expression.left
    assert first.span == call.span and inlined_arguments(first) == ()
    assert _location(first.left.span) == _location(call.span)
    assert first.left.left == argument
    assert inlined_arguments(first.left.left) == (
        InlinedArgument(
            call=call.span,
            function="small",
            position=1,
            parameter="v",
            type_name="Int",
            nullable=False,
        ),
    )
    copy = first.right.left
    assert type(copy) is NameExpr and copy != argument
    assert _location(copy.span) == _location(argument.span)
    assert inlined_arguments(copy) == inlined_arguments(first.left.left)
    nodes = _expression_nodes(expression)
    assert len({id(node) for node in nodes}) == len(nodes)
    assert len(set(nodes)) == len(nodes)


def test_a_parameter_named_like_a_function_never_replaces_the_call() -> None:
    shapes = (
        "shape T:\n    id: Int not null\n    lower: Text not null\n"
        "    note: Text nullable\n"
        'source t: T is postgres.table("t")\n'
    )
    called = _inlined(
        shapes + "def f(upper: Text nullable) -> Text nullable: return upper(upper)\n"
        "table r:\n    from t\n    select:\n        a = f(lower)\n"
        "        b = f(trim(note))\n"
    )
    written = _inlined(
        shapes + "table r:\n    from t\n    select:\n        a = upper(lower)\n"
        "        b = upper(trim(note))\n"
    )
    assert _shape(called) == _shape(written)
    assert (
        _errors(
            shapes
            + "def f(upper: Text nullable) -> Text nullable: return upper(upper)\n"
            "table r:\n    from t\n    select:\n        a = f(note)\n"
            "        b = f(trim(note))\n"
        )
        == []
    )


REFUSED = {
    "window_call": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = pos(id) window:\n            order by: id\n",
        (BODY_LINE + 4, 13, "a window computation", "pos"),
    ),
    "window_argument": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = lag(up(text)) window:\n            order by: id\n",
        (BODY_LINE + 4, 17, "a window computation", "up"),
    ),
    "partition_key": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = row_number() window:\n            partition by: up(text)\n"
        "            order by: id\n",
        (BODY_LINE + 5, 27, "a window computation", "up"),
    ),
    "named_window": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = row_number() window w\n    window w:\n        order by: up(text)\n",
        (BODY_LINE + 6, 19, "a window computation", "up"),
    ),
    "limit": (
        "table t:\n    from rows\n    select:\n        id\n    order by: id\n"
        "    limit up(3)\n",
        (BODY_LINE + 5, 11, "LIMIT", "up"),
    ),
    "grouped_order": (
        "table t:\n    from rows\n    group by: text\n    select:\n        text\n"
        "        c = count()\n    order by: up(text)\n",
        (BODY_LINE + 6, 15, "the ORDER BY of a grouped relation", "up"),
    ),
    "type_argument": (
        "shape S:\n    a: Decimal(abs(pos(9)), 2) not null\n",
        (BODY_LINE + 1, 20, "a type argument", "pos"),
    ),
    "type_argument_inside_limit": (
        "table t:\n    from rows\n    select:\n        id\n    order by: id\n"
        "    limit cast(3 as Decimal(pos(9), 0))\n",
        (BODY_LINE + 5, 29, "a type argument", "pos"),
    ),
    "window_frame": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = sum(id) window:\n            order by: id\n"
        "            rows between up(1) preceding and current row\n",
        (BODY_LINE + 6, 26, "a window computation", "up"),
    ),
    "source_connector": (
        'source s: Row is postgres.table(up("x"))\n',
        (BODY_LINE, 33, "a source connector", "up"),
    ),
}


@pytest.mark.parametrize(("relation", "expected"), REFUSED.values(), ids=REFUSED)
def test_a_def_call_is_refused_where_the_written_form_has_its_own_rule(
    relation: str, expected: tuple[int, int, str, str]
) -> None:
    line, column, position, name = expected
    assert _errors(SHAPES + DEFS + relation) == [
        (
            "PIE-S2397",
            line,
            column,
            f"A def call is not available in {position}: {name}",
        )
    ]


NULLS = {
    "null_argument": (
        'table t:\n    from rows\n    where pos(null) and up(null) == "A"\n'
        "    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got null",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 2,
                25,
                "Invalid argument for def up at "
                "position 1 (t): expected Text not null, got null",
            ),
        ],
    ),
    "null_only_argument": (
        "table t:\n    from rows\n    where pos(coalesce(null, null))\n"
        "    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got null",
            )
        ],
    ),
    "null_into_nullable": (
        "def opt(x: Int nullable) -> Bool nullable: return x > 0\n"
        "table t:\n    from rows\n    where opt(null)\n    select:\n        id\n",
        [],
    ),
    "null_body": (
        "def f(x: Int not null) -> Text not null: return null if x > 0 else null\n"
        "def g(x: Int not null) -> Text nullable: return null if x > 0 else null\n",
        [
            (
                "PIE-S2402",
                BODY_LINE,
                49,
                "Def f body is always null, but its declared return type is not null",
            )
        ],
    ),
    "null_operand_argument": (
        "table t:\n    from rows\n    where pos(id + null) and pos(-null)\n"
        "    select:\n        id\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                column,
                "Invalid argument for def pos at "
                "position 1 (x): expected Int not null, got null",
            )
            for column in (11, 30)
        ],
    ),
    "null_comparison_argument": (
        "def same(x: Text nullable) -> Text nullable: return x\n"
        "def flag(b: Bool nullable) -> Bool nullable: return b\n"
        "table t:\n    from rows\n    where flag(id == null)\n    select:\n"
        "        id\n        v = same(text == null)\n        w = up(text == null)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + line,
                13,
                f"Invalid argument for def {name} at position 1 ({parameter}): "
                f"expected Text {nullability}, got Bool of unknown nullability",
            )
            for line, name, parameter, nullability in (
                (7, "same", "x", "nullable"),
                (8, "up", "t", "not null"),
            )
        ],
    ),
    "null_operand_body": (
        "def f(x: Int not null) -> Int nullable: return x + null\n"
        "def g(x: Int not null) -> Int not null: return x + null\n",
        [
            (
                "PIE-S2402",
                BODY_LINE + 1,
                48,
                "Def g body is always null, but its declared return type is not null",
            )
        ],
    ),
    "unknown_body": (
        "def f(x: Int not null) -> Int nullable: "
        "return coalesce(null, null) if x > 0 else x\n",
        [
            (
                "PIE-S2402",
                BODY_LINE,
                48,
                "Def f body type is not known, so it "
                "cannot match declared return type Int",
            )
        ],
    ),
}


@pytest.mark.parametrize(("source", "expected"), NULLS.values(), ids=NULLS)
def test_null_is_nullable_and_an_unknown_body_fits_no_result(
    source: str, expected: list[tuple[str, int, int, str]]
) -> None:
    assert _errors(SHAPES + DEFS + source) == expected


def test_an_unknown_type_without_an_error_stays_unchecked() -> None:
    """Gradual typing: nothing is known about a field of a shapeless source,
    so its argument is not checked, as the same expression by hand is not."""
    source = (
        'source raw is postgres.table("raw")\n'
        + DEFS
        + "table t:\n    from raw\n    where pos(zz)\n    select:\n        zz\n"
    )
    assert [code for code, *_ in _errors(source)] == ["PIE-S2303"]


def test_a_satisfying_argument_matches_its_alias_canonical_type() -> None:
    source = (
        "type Percent = Int not null\nshape P:\n    pct: Percent not null\n"
        'source ps: P is postgres.table("ps")\n'
        + DEFS
        + "table t:\n    from ps\n    group by: pct\n    select:\n        pct\n"
        "        c = count()\n    satisfying: pos(pct)\n"
    )
    assert _errors(source) == []


def test_each_use_of_an_argument_reports_at_the_argument() -> None:
    source = (
        SHAPES
        + "def twice(x: Int nullable) -> Int nullable: return x + x\n"
        + "table t:\n    from rows\n    select:\n        id\n"
        + "        d = twice(nope + 1)\n"
    )
    assert (
        _errors(source) == [("PIE-S2102", BODY_LINE + 3, 19, "Unknown field: nope")] * 2
    )


def test_inlined_spans_are_real_locations() -> None:
    inlined = _inlined(
        SHAPES
        + "def twice(x: Int nullable) -> Int nullable: return x + x\n"
        + "table t:\n    from rows\n    select:\n        id\n"
        + "        d = twice(n)\n"
    )
    item = cast(SelectItem, cast(TableDef, inlined.definitions[-1]).select_items[1])
    sum_ = cast(BinaryExpr, item.expression)
    call = (BODY_LINE + 3, 13, BODY_LINE + 3, 21)
    argument = (BODY_LINE + 3, 19, BODY_LINE + 3, 20)
    assert _location(sum_.span) == call
    assert _location(sum_.left.span) == _location(sum_.right.span) == argument
    assert sum_.left != sum_.right


CASCADES = {
    "where": (
        "table t:\n    from rows\n    where f(note)\n    select:\n        id\n",
        [(BODY_LINE + 2, 11)],
    ),
    "three_uses_in_a_let": (
        "table t:\n    from rows\n    let: v = g(note)\n    select:\n        id\n"
        "        w = v\n",
        [(BODY_LINE + 2, 14)],
    ),
    "satisfying_first_use_unsupported": (
        "table t:\n    from rows\n    group by: note\n    select:\n        note\n"
        "        c = count()\n    satisfying: f(note)\n",
        [(BODY_LINE + 6, 17)],
    ),
}


@pytest.mark.parametrize(("relation", "calls"), CASCADES.values(), ids=CASCADES)
def test_a_mismatched_repeated_argument_is_reported_once(
    relation: str, calls: list[tuple[int, int]]
) -> None:
    """Every use of the argument fits nothing after the mismatch, so the
    expansion reports no operator error the user never wrote."""
    source = (
        SHAPES
        + "def f(x: Int nullable) -> Bool nullable: return x is null or x > 0\n"
        + "def g(x: Int nullable) -> Int nullable: return x + x * x\n"
        + relation
    )
    errors = [error for error in _errors(source) if error[0] != "PIE-S2327"]
    assert errors == [
        (
            "PIE-S2395",
            line,
            column,
            f"Invalid argument for def {'g' if 'let' in relation else 'f'} at "
            "position 1 (x): expected Int nullable, got Text nullable",
        )
        for line, column in calls
    ]


NESTED = {
    "operator": (
        "table t:\n    from rows\n    where twice(pos(note))\n    select:\n"
        "        id\n",
        ("pos", "x", 5, "Int not null", "Text nullable"),
    ),
    "builtin": (
        "table t:\n    from rows\n    select:\n        id\n        a = dbl(up(n))\n",
        ("up", "t", 7, "Text not null", "Int nullable"),
    ),
    "identity": (
        "table t:\n    from rows\n    select:\n        id\n        a = dbl(idt(n))\n",
        ("idt", "s", 7, "Text not null", "Int nullable"),
    ),
}


@pytest.mark.parametrize(("relation", "error"), NESTED.values(), ids=NESTED)
def test_a_mismatched_inner_call_in_a_repeated_argument_is_reported_once(
    relation: str, error: tuple[str, str, int, str, str]
) -> None:
    """Each copy of the argument keeps the inner call's parameter too, so
    no copy reports an operator or function error the user never wrote; an
    identity def's argument is not checked again for the call around it."""
    name, parameter, line, expected, got = error
    source = (
        SHAPES
        + DEFS
        + "def twice(b: Bool nullable) -> Bool nullable: return b and b\n"
        + "def dbl(t: Text nullable) -> Text nullable: return coalesce(t, t)\n"
        + "def idt(s: Text not null) -> Text not null: return s\n"
        + relation
    )
    assert _errors(source) == [
        (
            "PIE-S2395",
            BODY_LINE + line,
            17,
            f"Invalid argument for def {name} at position 1 ({parameter}): "
            f"expected {expected}, got {got}",
        )
    ]


def test_a_window_call_may_be_a_repeated_qualify_argument() -> None:
    """A window computation inside an argument is copied with its frame for
    every use of the parameter; nothing raises."""
    source = (
        SHAPES
        + "def twice(x: Int not null) -> Bool nullable: return x <= 2 and x <= 3\n"
        + "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        + "        twice(row_number() window:\n            order by:\n"
        + "                id\n            rows between 1 preceding and current row\n"
        + "        )\n"
    )
    inlined = _inlined(source)
    qualify = cast(Any, inlined.definitions[-1]).qualify_clause.expression
    left, right = qualify.left.left, qualify.right.left
    assert _shape(left) == _shape(right) and left != right
    assert left.spec.frame is not None
    assert _shape(left.spec.frame) == _shape(right.spec.frame)
    # A single file does not type QUALIFY (explain and emit-sql refuse it).
    assert _errors(source) == []


def test_concurrent_analyses_check_only_their_own_arguments() -> None:
    """Two analyses whose calls share every source position, run at once in
    two threads, each report only the parameters of their own def."""
    relation = "table t:\n    from rows\n    where f(n)\n    select:\n        id\n"
    programs = {
        name: SHAPES
        + f"def f(x: {name} not null) -> Bool not null: return x is null\n"
        + relation
        for name in ("Int", "Text")
    }
    expected = {
        name: [
            (
                "PIE-S2395",
                BODY_LINE + 1,
                11,
                f"Invalid argument for def f at position 1 (x): expected {name} "
                "not null, got Int nullable",
            )
        ]
        for name in programs
    }
    barrier = threading.Barrier(2)

    def run(name: str) -> list[list[tuple[str, int, int, str]]]:
        barrier.wait()
        return [_errors(programs[name]) for _ in range(25)]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(programs, pool.map(run, programs)))
    for name, runs in results.items():
        assert runs == [expected[name]] * 25


@pytest.mark.parametrize(
    "function", ["now", "random", "current_timestamp", "gen_random_uuid"]
)
def test_no_volatile_function_reaches_a_repeated_argument(function: str) -> None:
    """A parameter used twice writes its argument twice in SQL, which keeps
    its meaning because Pietto has no volatile function to pass."""
    source = SHAPES + (
        "def twice(v: Int nullable) -> Bool nullable: return v > 0 and v < 9\n"
        f"table t:\n    from rows\n    where twice({function}())\n"
        "    select:\n        id\n"
    )
    assert (
        _errors(source)
        == [("PIE-S2103", BODY_LINE + 1, 17, f"Unknown function: {function}")] * 2
    )


def _expression_nodes(expression: Any) -> list[Any]:
    found: list[Any] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        found.append(node)
        pending.extend(
            child
            for item in fields(node)
            if item.name != "span"
            for child in (
                getattr(node, item.name)
                if type(getattr(node, item.name)) is tuple
                else (getattr(node, item.name),)
            )
            if is_dataclass(child) and hasattr(child, "span")
        )
    return found
