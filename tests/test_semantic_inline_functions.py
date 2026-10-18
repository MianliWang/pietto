"""Pure inline ``def`` functions: definition checks, call checks and inlining.

A call is replaced by the def body with each argument in place of its
parameter before any call site is typed. SQL byte identity lives with the SQL
owners; project checks live with the project owners.
"""

from __future__ import annotations

import functools
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, is_dataclass
from types import ModuleType
from typing import Any, cast

import pytest

from pietto._inline_argument import InlinedArgument
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    FunctionDef,
    NameExpr,
    Script,
    SelectItem,
    Span,
    TableDef,
    inlined_arguments,
)
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic import analyzer as analyzer_module
from pietto.semantic import expressions as expressions_module
from pietto.semantic import inline_functions as inline_module
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
SCALARS = (
    "Bool, Int, Float, Decimal, Text, Date, Timestamp or UUID, without arguments, "
    "or an alias of one declared in this file without arguments or `ensure`"
)


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
    "enum_any_and_type_arguments": (
        "type Percent = Int not null\nenum Status: a, b\n"
        "def f(p: Percent not null, s: Status not null, a: Any not null, "
        "d: Decimal(9, 2) not null) -> Bool not null: "
        "return p is null and s is null and a is null and d is null\n",
        [
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
    # A body is checked at the def, where an error in a call's argument is
    # reported at each use that the expansion makes.
    "an_error_in_a_call_inside_a_body": (
        "def twice(b: Bool nullable) -> Bool nullable: return b or b\n"
        "def h(y: Int nullable) -> Bool nullable: return twice(y == null)\n",
        [
            (
                "PIE-S2105",
                2,
                55,
                "Invalid operands for operator ==: comparison with null is "
                "never true; write `is null` instead",
            )
        ]
        * 2,
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
    "satisfying_aggregate_let": (
        "def nn(x: Int not null) -> Int not null: return x\n"
        "table t:\n    from rows\n    let:\n        f = n\n    group by: text\n"
        "    select:\n        text\n        c = count(f)\n"
        "    satisfying: count(nn(f)) > 0\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 9,
                23,
                "Invalid argument for def nn at "
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


ALIASES = (
    "type Percent = Int not null\ntype Share = Percent nullable\n"
    "type Positive = Int not null:\n    ensure self > 0\n"
    "type Code = Text(max = 3) not null\ntype Tag = Code not null\n"
    "enum Status: a, b\ntype State = Status not null\n"
)


def test_a_def_reads_an_alias_of_its_file_as_the_type_it_expands_to() -> None:
    """A signature alias is its base type, as an operator reads one: the
    body and every argument are checked against that type."""
    source = (
        ALIASES
        + SHAPES
        + "def bump(p: Share nullable) -> Percent nullable: return p + 1\n"
        "table t:\n    from rows\n    select:\n        id\n"
        "        b = bump(bump(n))\n        c = bump(text)\n"
    )
    assert _errors(source) == [
        (
            "PIE-S2395",
            22,
            13,
            "Invalid argument for def bump at position 1 (p): "
            "expected Int nullable, got Text not null",
        )
    ]


def test_a_def_refuses_an_alias_with_ensure_or_type_arguments_or_of_an_enum() -> None:
    source = ALIASES + (
        "def f(a: Positive not null, b: Tag not null) -> State nullable: "
        "return a > 0 and b == ''\n"
    )
    assert _errors(source) == [
        (
            "PIE-S2397",
            9,
            column,
            f"Def f {role} has type {name}; a def parameter or result type is "
            f"exactly {SCALARS}",
        )
        for column, role, name in (
            (10, "parameter a", "Positive"),
            (32, "parameter b", "Tag"),
            (49, "result", "State"),
        )
    ]


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


# Def arguments that read ARG in a compound expression; a `let:` name four
# characters long, as `null` is, keeps every column when the literal is
# written in its place.
NULL_LET_ARGUMENTS = (
    "def bb(p: Bool not null) -> Bool not null: return p is null\n"
    "table t:\n    from rows\n    let:\n        nill = null\n"
    "    where pos(coalesce(ARG, n))\n    select:\n        id\n"
    "        a = up(lower(ARG))\n        b = pos(ARG if id > 0 else 1)\n"
    "        c = bb(id in (ARG, 2))\n        d = pos(len(up(ARG)))\n"
)
# Def arguments that read `let:` names whose values read one bound to null;
# each placeholder is the name, or its value written in its place.
WRITTEN_LETS = (
    "def bb(p: Bool not null) -> Bool not null: return p is null\n"
    "def same(x: Int nullable) -> Int nullable: return x\n"
    "table t:\n    from rows\n    let:\n        nill = null\n"
    "        j1 = coalesce(nill, n)\n        j2 = j1 + 1\n"
    "        j3 = nill if id > 0 else 1\n        j4 = lower(nill)\n"
    "        j5 = id in (nill, 2)\n        j6 = same(nill)\n"
    "    where pos({J1})\n    select:\n        id\n        a = pos({J2})\n"
    "        b = pos({J3})\n        c = up({J4})\n        d = bb({J5})\n"
    "        e = pos({J6})\n"
)
WRITTEN = {
    "J1": "coalesce(null, n)",
    "J2": "coalesce(null, n) + 1",
    "J3": "null if id > 0 else 1",
    "J4": "lower(null)",
    "J5": "id in (null, 2)",
    "J6": "same(null)",
}
# Def arguments that read `let:` names whose values are ill-typed once the
# null they read is written in; each placeholder is the name, or its value
# written in its place, which starts where the name does. `m` reads one
# outside a def argument.
ILL_TYPED_LETS = (
    "def nt(x: Text not null) -> Text not null: return x\n"
    "def bb(p: Bool not null) -> Bool not null: return p is null\n"
    "def tw(x: Text not null) -> Bool nullable: return x == x\n"
    "table t:\n    from rows\n    let:\n        nill = null\n"
    "        i1 = coalesce(nill, 1)\n        i2 = upper(nill) + 1\n"
    "        i3 = lower(nill) * 2\n        i4 = not lower(nill)\n"
    "        i5 = coalesce(nill, text, 1)\n        i6 = text if nill else 1\n"
    "        i7 = len(nill) + text\n        i8 = lower(i1), i9 = lower(i1) is null\n"
    "    where pos({I2})\n    select:\n        id\n"
    "        a = nt(lower({I1}))\n        b = pos({I3})\n        c = bb({I4})\n"
    "        d = pos({I5})\n        e = pos({I6})\n        f = pos({I7})\n"
    "        g = nt({I8})\n        h = tw(lower({I1}))\n"
    "        k = nt(nt(lower({I1})))\n        m = i2\n"
    "        n = bb(lower({I1}) is null)\n        o = bb({I9})\n"
    "        p = bb(coalesce(lower({I1}) == 'a', false))\n"
    "        q = nt(text if lower({I1}) == 'a' else 'b')\n"
    "        r = bb(lower({I1}) == 'a')\n        s = nt(substr(lower({I1}), 1))\n"
)
ILL_TYPED = {
    "I1": "coalesce(null, 1)",
    "I2": "upper(null) + 1",
    "I3": "lower(null) * 2",
    "I4": "not lower(null)",
    "I5": "coalesce(null, text, 1)",
    "I6": "text if null else 1",
    "I7": "len(null) + text",
    "I8": "lower(coalesce(null, 1))",
    "I9": "lower(coalesce(null, 1)) is null",
}
NOT_NUMERIC = "Invalid operands for operator {}: expected numeric operands"
LOWER_OF_INT = (
    "Invalid argument type for function lower at position 1: expected Text, got Int"
)
ILL_TYPED_ERRORS = [
    ("PIE-S2105", BODY_LINE + 15, 15, NOT_NUMERIC.format("+")),
    ("PIE-S2104", BODY_LINE + 18, 16, LOWER_OF_INT),
    ("PIE-S2105", BODY_LINE + 19, 17, NOT_NUMERIC.format("*")),
    (
        "PIE-S2105",
        BODY_LINE + 20,
        16,
        "Invalid operands for operator not: expected Bool operand",
    ),
    (
        "PIE-S2104",
        BODY_LINE + 21,
        17,
        "Invalid argument types for function coalesce: expected same canonical type",
    ),
    (
        "PIE-S2105",
        BODY_LINE + 22,
        17,
        "Invalid operands for operator conditional: "
        "expected same canonical branch types",
    ),
    ("PIE-S2105", BODY_LINE + 23, 17, NOT_NUMERIC.format("+")),
    ("PIE-S2104", BODY_LINE + 24, 16, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 25, 16, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 26, 19, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 28, 16, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 29, 16, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 30, 25, LOWER_OF_INT),
    ("PIE-S2104", BODY_LINE + 31, 24, LOWER_OF_INT),
    (
        "PIE-S2395",
        BODY_LINE + 32,
        13,
        "Invalid argument for def bb at position 1 (p): "
        "expected Bool not null, got Bool of unknown nullability",
    ),
    ("PIE-S2104", BODY_LINE + 32, 16, LOWER_OF_INT),
    (
        "PIE-S2104",
        BODY_LINE + 33,
        16,
        "Invalid arguments for function substr: expected 3, got 2",
    ),
    ("PIE-S2104", BODY_LINE + 33, 23, LOWER_OF_INT),
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
        "def opt(x: Int nullable) -> Int nullable: return coalesce(x, 0)\n"
        "table t:\n    from rows\n    where opt(null) > 0\n    select:\n        id\n",
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
        "table t:\n    from rows\n    where flag(id == (id + null))\n    select:\n"
        "        id\n        v = same(id == (id + null))\n"
        "        w = up(id == (id + null))\n",
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
    # A comparison with the null literal is never true (PIE-S2105), in an
    # argument as by hand: it is reported once at the argument, however many
    # times the body uses it, as any error inside an argument is, and the
    # argument is then not checked against the parameter, so no PIE-S2395
    # restates it.
    "null_literal_comparison_argument": (
        "def flag(b: Bool not null) -> Bool nullable: return b or b\n"
        "table t:\n    from rows\n    where flag(id == null)\n    select:\n"
        "        id\n        w = up(text != null)\n",
        [
            (
                "PIE-S2105",
                BODY_LINE + 3,
                16,
                "Invalid operands for operator ==: comparison with null is "
                "never true; write `is null` instead",
            ),
            (
                "PIE-S2105",
                BODY_LINE + 6,
                16,
                "Invalid operands for operator !=: comparison with null is "
                "never true; write `is not null` instead",
            ),
        ],
    ),
    # A null argument makes a comparison of the body never true; it is
    # reported where the expansion is typed, at the call.
    "null_argument_in_a_body_comparison": (
        "def low(x: Int nullable) -> Bool nullable: return x < 3\n"
        "table t:\n    from rows\n    where low(null)\n    select:\n        id\n",
        [
            (
                "PIE-S2105",
                BODY_LINE + 3,
                11,
                "Invalid operands for operator <: comparison with null is never true",
            )
        ],
    ),
    # A null argument for a nullable parameter makes a cast of the body a cast
    # of null; one that does not fit its `not null` parameter is PIE-S2395 alone.
    "null_argument_in_a_body_cast": (
        "def fl(x: Int not null) -> Float nullable: return cast(x as Float)\n"
        "def fn(x: Int nullable) -> Float nullable: return cast(x as Float)\n"
        "table t:\n    from rows\n    select:\n        id\n"
        "        a = fl(null)\n        b = fn(null)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 6,
                13,
                "Invalid argument for def fl at position 1 (x): "
                "expected Int not null, got null",
            ),
            (
                "PIE-S2105",
                BODY_LINE + 7,
                13,
                "Invalid cast: cast(null as Float) is not supported; "
                "expected cast(Int as Float), the only supported cast",
            ),
        ],
    ),
    # A `let:` name bound to null, also through other lets, is the null
    # literal wherever the expansion reads it, as emission inlines it.
    "null_let_argument": (
        "table t:\n    from rows\n    let:\n        k = null\n        k2 = k\n"
        "        k3 = k2\n    where pos(k) and pos(k3)\n    select:\n        id\n"
        "        a = up(k2)\n        b = pos(k + 1)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + line,
                column,
                f"Invalid argument for def {name} at position 1 ({parameter}): "
                f"expected {expected} not null, got null",
            )
            for line, column, name, parameter, expected in (
                (6, 11, "pos", "x", "Int"),
                (6, 22, "pos", "x", "Int"),
                (9, 13, "up", "t", "Text"),
                (10, 13, "pos", "x", "Int"),
            )
        ],
    ),
    # Such a let that does not fit its `not null` parameter is PIE-S2395
    # alone, also where the body compares or casts it; for a nullable
    # parameter the cast is a cast of null, as with the literal.
    "null_let_argument_in_a_body_cast_or_comparison": (
        "def fl(x: Int not null) -> Float nullable: return cast(x as Float)\n"
        "def fn(x: Int nullable) -> Float nullable: return cast(x as Float)\n"
        "table t:\n    from rows\n    let:\n        k = null\n        k2 = k\n"
        "    where pos(k2)\n    select:\n        id\n        a = fl(k)\n"
        "        b = fn(k2)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 7,
                11,
                "Invalid argument for def pos at position 1 (x): "
                "expected Int not null, got null",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 10,
                13,
                "Invalid argument for def fl at position 1 (x): "
                "expected Int not null, got null",
            ),
            (
                "PIE-S2105",
                BODY_LINE + 11,
                13,
                "Invalid cast: cast(null as Float) is not supported; "
                "expected cast(Int as Float), the only supported cast",
            ),
        ],
    ),
    # An argument that reads such a let is checked as emission writes it: the
    # null literal in the let's place takes its type from where it stands, and
    # a call inside the argument that it does not fit is the one error.
    "null_let_inside_an_argument": (
        NULL_LET_ARGUMENTS.replace("ARG", "nill"),
        [
            (
                "PIE-S2395",
                BODY_LINE + line,
                column,
                f"Invalid argument for def {name} at position 1 ({parameter}): "
                f"expected {expected} not null, got {actual}",
            )
            for line, column, name, parameter, expected, actual in (
                (5, 11, "pos", "x", "Int", "Int nullable"),
                (8, 13, "up", "t", "Text", "Text nullable"),
                (9, 13, "pos", "x", "Int", "Int nullable"),
                (10, 13, "bb", "p", "Bool", "Bool nullable"),
                (11, 21, "up", "t", "Text", "null"),
            )
        ],
    ),
    # A let bound to another always-null value is null too; one whose binding
    # has an error of its own, also through an alias, is not checked, as an
    # argument with an error of its own is not.
    "always_null_let_argument": (
        "def nn(x: Int not null) -> Int not null: return x\n"
        "def plusn(x: Int nullable) -> Int nullable: return x + 1\n"
        "table t:\n    from rows\n    let:\n"
        "        m = id + null\n        m2 = -null\n        m3 = coalesce(null, null)\n"
        "        m4 = plusn(null)\n        m5 = m + 1\n"
        "        e = id == null\n        f = nn(null)\n        g = f\n"
        "        h = zz + null\n    select:\n        id\n"
        "        a = pos(m)\n        b = pos(m2)\n        c = pos(m3)\n"
        "        d = pos(m4)\n        q = pos(m5)\n        w = pos(e)\n"
        "        x = pos(f)\n        y = pos(g)\n        z = pos(h)\n",
        [
            (
                "PIE-S2105",
                BODY_LINE + 10,
                13,
                "Invalid operands for operator ==: comparison with null is "
                "never true; write `is null` instead",
            ),
            (
                "PIE-S2395",
                BODY_LINE + 11,
                13,
                "Invalid argument for def nn at position 1 (x): "
                "expected Int not null, got null",
            ),
            ("PIE-S2102", BODY_LINE + 13, 13, "Unknown field: zz"),
            *(
                (
                    "PIE-S2395",
                    BODY_LINE + line,
                    13,
                    "Invalid argument for def pos at position 1 (x): "
                    "expected Int not null, got null",
                )
                for line in range(16, 21)
            ),
        ],
    ),
    # A `let:` name that an aggregate reads is checked with its binding's type,
    # so `sum(nn(nill))` is PIE-S2315 alone, as `sum(nn(null))` is. `min` and
    # `max` read no `let:` name, so the name is an unknown field there, with
    # or without a def.
    "null_let_in_an_aggregate_argument": (
        "def nn(x: Int not null) -> Int not null: return x\n"
        "table t:\n    from rows\n    let:\n        nill = null\n"
        "    where pos(nill)\n    group by: id\n    select:\n        id\n"
        "        c = sum(nn(nill))\n        m = max(nn(nill))\n"
        "        l = min(nill)\n",
        [
            (
                "PIE-S2395",
                BODY_LINE + 5,
                11,
                "Invalid argument for def pos at position 1 (x): "
                "expected Int not null, got null",
            ),
            (
                "PIE-S2315",
                BODY_LINE + 9,
                13,
                "Aggregate function sum requires a direct field argument; "
                "expression arguments are not supported yet",
            ),
            ("PIE-S2102", BODY_LINE + 10, 20, "Unknown field: nill"),
            ("PIE-S2102", BODY_LINE + 11, 17, "Unknown field: nill"),
        ],
    ),
    # Each argument reads a `let:` name whose value reads one bound to null;
    # it is checked with every value written in, as emission writes it.
    "let_reading_a_null_let": (
        WRITTEN_LETS.format(**{key: key.lower() for key in WRITTEN}),
        [
            (
                "PIE-S2395",
                BODY_LINE + line,
                column,
                f"Invalid argument for def {name} at position 1 ({parameter}): "
                f"expected {expected} not null, got {actual}",
            )
            for line, column, name, parameter, expected, actual in (
                (12, 11, "pos", "x", "Int", "Int nullable"),
                (15, 13, "pos", "x", "Int", "Int of unknown nullability"),
                (16, 13, "pos", "x", "Int", "Int nullable"),
                (17, 13, "up", "t", "Text", "Text nullable"),
                (18, 13, "bb", "p", "Bool", "Bool nullable"),
                (19, 13, "pos", "x", "Int", "null"),
            )
        ],
    ),
    "null_comparison_body": (
        "def f(x: Int nullable) -> Bool nullable: return x == null\n",
        [
            (
                "PIE-S2105",
                BODY_LINE,
                49,
                "Invalid operands for operator ==: comparison with null is "
                "never true; write `is null` instead",
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


def test_an_argument_reads_a_null_let_as_the_literal_written_in_its_place() -> None:
    """The literal itself, written where the let is read, gives the same
    errors: one at the innermost call it does not fit, after which it is
    Unknown to every call around it."""
    assert (
        _errors(SHAPES + DEFS + NULL_LET_ARGUMENTS.replace("ARG", "null"))
        == NULLS["null_let_inside_an_argument"][1]
    )


def test_an_argument_reads_each_let_as_its_value_written_in_its_place() -> None:
    """The values themselves, written where their names are read, give the
    same errors at the same calls."""
    assert (
        _errors(SHAPES + DEFS + WRITTEN_LETS.format(**WRITTEN))
        == NULLS["let_reading_a_null_let"][1]
    )


@pytest.mark.parametrize(
    "spelling",
    [{key: key.lower() for key in ILL_TYPED}, ILL_TYPED],
    ids=["let_names", "values_written_in"],
)
def test_an_argument_ill_typed_once_its_lets_are_written_in_is_an_error(
    spelling: dict[str, str],
) -> None:
    """An argument whose `let:` values are ill-typed once the null they read
    is written in reports the errors the values written by hand report, where
    they start, once however many times the body uses it, also inside a value
    whose type is known without them (`is null`, `coalesce(..., false)`, a
    conditional's condition), next to an error of its own (`substr`), and is
    checked against its parameter when it still has a type (`r`), as those
    values are. A read outside a def argument (`m = i2`) is not checked so."""
    assert _errors(SHAPES + DEFS + ILL_TYPED_LETS.format(**spelling)) == (
        ILL_TYPED_ERRORS
    )


def test_a_deep_let_value_read_deep_in_an_expression_is_written_in() -> None:
    """A `let:` value is written in where typing starts, not where the
    argument stands deep in its expression, so its depth adds to none."""
    chain = " + 1" * 300
    source = (
        SHAPES + "def nn(x: Int not null) -> Int not null: return x\n"
        "table t:\n    from rows\n    let:\n        nill = null\n"
        f"        jj = coalesce(nill, n){chain}\n    select:\n        id\n"
        f"        a = nn(jj){chain}\n"
    )
    assert _errors(source) == [
        (
            "PIE-S2395",
            16,
            13,
            "Invalid argument for def nn at position 1 (x): "
            "expected Int not null, got Int of unknown nullability",
        )
    ]


def test_an_unknown_type_without_an_error_stays_unchecked() -> None:
    """Gradual typing: nothing is known about a field of a shapeless source,
    so its argument is not checked, as the same expression by hand is not."""
    source = (
        'source raw is postgres.table("raw")\n'
        + DEFS
        + "table t:\n    from raw\n    where pos(zz)\n    select:\n        zz\n"
    )
    assert [code for code, *_ in _errors(source)] == ["PIE-S2303"]


def test_a_let_bound_to_null_is_null_over_an_unknown_row() -> None:
    """A `let:` name is its value over a shapeless source too, as emission
    inlines it: one bound to null is null, and one bound to a field of
    unknown type stays unchecked."""
    source = (
        'source raw is postgres.table("raw")\n'
        + DEFS
        + "table t:\n    from raw\n    let:\n        k = null\n        z = zz\n"
        "    where pos(z) and pos(k)\n    select:\n        zz\n"
    )
    assert _errors(source) == [
        ("PIE-S2303", 1, 1, "Source raw has no bound shape; row schema is unknown"),
        (
            "PIE-S2395",
            9,
            22,
            "Invalid argument for def pos at position 1 (x): "
            "expected Int not null, got null",
        ),
    ]


def test_a_satisfying_argument_matches_its_alias_canonical_type() -> None:
    source = (
        "type Percent = Int not null\nshape P:\n    pct: Percent not null\n"
        'source ps: P is postgres.table("ps")\n'
        + DEFS
        + "table t:\n    from ps\n    group by: pct\n    select:\n        pct\n"
        "        c = count()\n    satisfying: pos(pct)\n"
    )
    assert _errors(source) == []


def test_each_use_of_an_argument_reports_at_the_argument_once() -> None:
    source = (
        SHAPES
        + "def twice(x: Int nullable) -> Int nullable: return x + x\n"
        + "table t:\n    from rows\n    select:\n        id\n"
        + "        d = twice(nope + 1)\n"
    )
    assert _errors(source) == [("PIE-S2102", BODY_LINE + 3, 19, "Unknown field: nope")]


REPEATING_DEFS = (
    "def twice(b: Bool nullable) -> Bool nullable: return b or b\n"
    "def thrice(b: Bool nullable) -> Bool nullable: return b and b or not b\n"
    "def either(a: Bool nullable, b: Bool nullable) -> Bool nullable: return a or b or a\n"
    "def dbl(x: Int nullable) -> Int nullable: return x + x\n"
    "def sum2(x: Int not null) -> Int nullable: return x + x\n"
    "def low(x: Int nullable) -> Bool nullable: return x < 3 or x < 4\n"
    "def one(b: Bool nullable) -> Bool nullable: return b\n"
    "def listed(x: Int nullable) -> Bool nullable: return x in (1, 2) or x in (7)\n"
)
NULL_TEST = "comparison with null is never true"
IS_NULL = f"Invalid operands for operator ==: {NULL_TEST}; write `is null` instead"
ONCE = {
    "where": (
        "    where twice(id == null)\n    select:\n        id\n",
        [("PIE-S2105", 2, 17, IS_NULL)],
    ),
    "three_uses": (
        "    select:\n        id\n        a = thrice(n != null)\n",
        [
            (
                "PIE-S2105",
                4,
                20,
                f"Invalid operands for operator !=: {NULL_TEST}; "
                "write `is not null` instead",
            )
        ],
    ),
    "let": (
        "    let: k = twice(nope == 1)\n    select:\n        id\n        a = k\n",
        [("PIE-S2102", 2, 20, "Unknown field: nope")],
    ),
    "order_by": (
        "    select:\n        id\n    order by:\n        dbl(len(substr(text, 0, 2)))\n",
        [
            (
                "PIE-S2104",
                5,
                17,
                "Invalid arguments for function substr: start must be a positive "
                "Int literal and count must be a non-negative Int literal",
            )
        ],
    ),
    "grouped_select": (
        "    group by: id\n    select:\n        id\n        a = twice(id == null)\n",
        [
            (
                "PIE-S2319",
                5,
                13,
                "Grouped scalar projection expressions are not supported yet",
            ),
            ("PIE-S2105", 5, 19, IS_NULL),
        ],
    ),
    "aggregate_argument": (
        "    group by: id\n    select:\n        id\n        s = dbl(sum(nope))\n",
        [
            (
                "PIE-S2310",
                5,
                13,
                "Aggregate projection must be a direct aggregate call; composition "
                "around sum() is not supported yet",
            ),
            ("PIE-S2102", 5, 21, "Unknown field: nope"),
        ],
    ),
    "unknown_function": (
        "    select:\n        id\n        a = twice(nope(id) == 1)\n",
        [("PIE-S2103", 4, 19, "Unknown function: nope")],
    ),
    "operand_type": (
        "    select:\n        id\n        a = dbl(id + 'x')\n",
        [
            (
                "PIE-S2105",
                4,
                17,
                "Invalid operands for operator +: expected numeric operands",
            )
        ],
    ),
    "nested_call": (
        "    select:\n        id\n        a = twice(twice(id == null))\n",
        [("PIE-S2105", 4, 25, IS_NULL)],
    ),
    # Every copy's error still keeps the always-null argument of sum2 from
    # being checked against its not-null parameter: no PIE-S2395.
    "nested_always_null": (
        "    select:\n        id\n        a = sum2(dbl(nope + null))\n",
        [("PIE-S2102", 4, 22, "Unknown field: nope")],
    ),
    "same_text_in_two_arguments": (
        "    select:\n        id\n        a = either(id == null, id == null)\n",
        [("PIE-S2105", 4, 20, IS_NULL), ("PIE-S2105", 4, 32, IS_NULL)],
    ),
    "same_text_in_two_calls": (
        "    select:\n        id\n        a = twice(id == null)\n"
        "        c = twice(id == null)\n",
        [("PIE-S2105", 4, 19, IS_NULL), ("PIE-S2105", 5, 19, IS_NULL)],
    ),
    # Two body comparisons that a null argument makes never true are both at
    # the call, and reported once there, also for a call inside an argument.
    "body_at_the_call": (
        "    where low(null) and twice(id == null)\n    select:\n        id\n",
        [
            ("PIE-S2105", 2, 11, f"Invalid operands for operator <: {NULL_TEST}"),
            ("PIE-S2105", 2, 31, IS_NULL),
        ],
    ),
    "body_at_a_call_in_an_argument": (
        "    where one(low(null)) and low(null)\n    select:\n        id\n",
        [
            ("PIE-S2105", 2, 15, f"Invalid operands for operator <: {NULL_TEST}"),
            ("PIE-S2105", 2, 30, f"Invalid operands for operator <: {NULL_TEST}"),
        ],
    ),
    "body_at_the_call_in_satisfying": (
        "    group by: id\n    select:\n        id\n        c = count()\n"
        "    satisfying: listed(c)\n",
        [
            (
                "PIE-S2327",
                6,
                17,
                "Unsupported satisfying expression form: `in` list",
            )
        ],
    ),
}


@pytest.mark.parametrize(("relation", "expected"), ONCE.values(), ids=ONCE)
def test_an_error_in_a_call_is_reported_once_however_often_it_is_typed(
    relation: str, expected: list[tuple[str, int, int, str]]
) -> None:
    """The expansion types the body at the call and its argument once per use,
    each copy at the argument's own text; the call is written once, so each
    error in it is reported once at its text. Different arguments or calls are
    different text."""
    first = BODY_LINE + REPEATING_DEFS.count("\n")
    source = SHAPES + DEFS + REPEATING_DEFS + "table t:\n    from rows\n" + relation
    assert _errors(source) == [
        (code, first + line, column, message)
        for code, line, column, message in expected
    ]


def test_an_equal_error_outside_a_def_call_is_still_repeated() -> None:
    """Only a repeat inside the text of a def call is dropped: an index that
    names an unknown field twice reports it twice, as without a def, and the
    call in its predicate reports its error once."""
    source = (
        "shape S:\n    a: Int nullable\n"
        "    index i on missing, missing when twice(a == null)\n"
        "def twice(b: Bool nullable) -> Bool nullable: return b or b\n"
    )
    unknown = ("PIE-S2502", 3, 5, "Unknown target field in shape S: missing")
    assert _errors(source) == [
        unknown,
        unknown,
        ("PIE-S2503", 3, 5, "Duplicate target field in index i: missing"),
        ("PIE-S2105", 3, 44, IS_NULL),
    ]


UNKNOWN_ROW = (
    'source u is postgres.table("u")\n'
    "def twice(a: Int nullable) -> Int nullable: return a + a\n"
    "def same(a: Text nullable) -> Bool nullable: return a == a\n"
    "table t:\n    from u\n    select:\n        v = {call}\n"
)
NO_SHAPE = ("PIE-S2303", 1, 1, "Source u has no bound shape; row schema is unknown")
UNKNOWN_ROW_ONCE = {
    "unknown_function": ("twice(foo(x))", "PIE-S2103", "Unknown function: foo"),
    "window_without_window": (
        "twice(lag(x))",
        "PIE-S2103",
        "Window function needs a `window` specification: lag (write `lag(...) "
        "window:` in a SELECT item, with an indented `order by:`)",
    ),
    "arity": (
        "twice(sign(x, x))",
        "PIE-S2104",
        "Invalid arguments for function sign: expected 1, got 2",
    ),
    "substr_bounds": (
        "same(substr(x, 0, 1))",
        "PIE-S2104",
        "Invalid arguments for function substr: start must be a positive Int "
        "literal and count must be a non-negative Int literal",
    ),
    "cast_target": (
        "same(cast(x as Text))",
        "PIE-S2105",
        "Invalid cast: cast(unknown as Text) is not supported; expected "
        "cast(Int as Float), the only supported cast",
    ),
}


@pytest.mark.parametrize(
    ("call", "code", "message"), UNKNOWN_ROW_ONCE.values(), ids=UNKNOWN_ROW_ONCE
)
def test_a_check_that_reads_no_argument_type_runs_once_in_a_call_over_an_unknown_row(
    call: str, code: str, message: str
) -> None:
    """A field of a source without a shape is of unknown type, which hides no
    check that reads no argument's type: as written by hand, it is reported
    at the argument, and once, though the body uses the argument twice."""
    column = 13 + call.index("(") + 1
    assert _errors(UNKNOWN_ROW.format(call=call)) == [
        NO_SHAPE,
        (code, 7, column, message),
    ]


def _plus(levels: int, first: str) -> str:
    """``first + 1 + ... + 1``, nesting ``levels`` levels with ``first`` deepest."""
    return " + ".join([first, *["1"] * (levels - 1)])


DEEP_DEF = "def deep(x: Int nullable) -> Int nullable: return " + _plus(60, "x") + "\n"
UNUSED = "Def bad parameter x is not used in its body; every parameter must be used"
RECURSION_LIMIT = "Semantic analysis recursion limit exceeded while processing source."


@pytest.mark.parametrize(
    ("levels", "extra", "expected"),
    [
        (391, "", []),
        (392, "", [("PIE-S2006", 1, 1, RECURSION_LIMIT)]),
        (
            392,
            "def bad(x: Int nullable) -> Int nullable: return 1\n",
            [("PIE-S2397", 2, 9, UNUSED)],
        ),
    ],
    ids=["450_levels", "451_levels", "def_error_first"],
)
def test_the_expression_bound_counts_a_call_as_its_expansion(
    levels: int, extra: str, expected: list[tuple[str, int, int, str]]
) -> None:
    """The call sits `levels` deep and its body nests 60 more levels, so the
    written expression stays far below 450 levels while the inlined one, which
    analysis reads, reaches 450 and then 451. A def error stops the check
    before the bound is measured."""
    source = (
        DEEP_DEF
        + extra
        + SHAPES
        + "table t:\n    from rows\n    select:\n"
        + f"        v = {_plus(levels, 'deep(n)')}\n"
    )
    assert _errors(source) == expected


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


def _def_chain(count: int) -> str:
    """Each def calls the one before it; none is called."""

    return "def f0(x: Int not null) -> Int not null: return x\n" + "".join(
        f"def f{i}(x: Int not null) -> Int not null: return f{i - 1}(x)\n"
        for i in range(1, count)
    )


def _wide_calls(count: int) -> str:
    """Twenty calls to a def with ``count`` parameters."""

    parameters = ", ".join(f"a{i}: Int not null" for i in range(count))
    body = ", ".join(f"a{i}" for i in range(count))
    call = ", ".join(["id"] * count)
    return (
        SHAPES
        + f"def g({parameters}) -> Int not null: return coalesce({body})\n"
        + "table t:\n    from rows\n    select:\n        id\n"
        + "".join(f"        v{i} = g({call})\n" for i in range(20))
    )


def _refused_nest(count: int) -> str:
    """``count`` nested calls around one with a wrong argument count."""

    return (
        SHAPES
        + DEFS
        + "table t:\n    from rows\n    select:\n        id\n        v = "
        + "up(" * count
        + "text, text"
        + ")" * count
        + "\n"
    )


class _OverBudget(Exception):
    pass


def _inlining_lines(source: str, budget: int) -> int:
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    return _module_lines(functools.partial(inline_functions, parsed.ast), budget)


def _module_lines(
    run: Callable[[], object], budget: int, module: ModuleType = inline_module
) -> int:
    """Lines ``run`` runs in ``module``, the inlining module by default, an
    operation count that does not depend on the machine; past ``budget`` the
    run stops."""

    lines = 0

    def count(frame: Any, event: str, arg: object) -> Any:
        nonlocal lines
        if event == "line":
            lines += 1
            if lines > budget:
                raise _OverBudget
        return count

    def enter(frame: Any, event: str, arg: object) -> Any:
        return count if frame.f_code.co_filename == module.__file__ else None

    previous = sys.gettrace()
    sys.settrace(enter)
    try:
        run()
    except _OverBudget:
        pass
    finally:
        sys.settrace(previous)
    return lines


@pytest.mark.parametrize(
    ("build", "size"),
    [(_def_chain, 1000), (_wide_calls, 100), (_refused_nest, 40)],
    ids=["def_chain", "parameters_per_call", "nested_refused_calls"],
)
def test_inlining_work_grows_linearly(build: Callable[[int], str], size: int) -> None:
    """Twice the input costs at most about twice the work: recursion is found
    by one pass over the call graph, a def is measured once, and a refused
    call marks the calls around it without walking their arguments again."""

    work = _inlining_lines(build(size), sys.maxsize)
    budget = work * 21 // 10
    assert _inlining_lines(build(2 * size), budget) <= budget


def _repeated_errors(count: int) -> str:
    """``count`` calls, each with an unknown field the body reads 32 times."""

    return (
        SHAPES
        + "def many(x: Int nullable) -> Int nullable: return "
        + " + ".join(["x"] * 32)
        + "\ntable t:\n    from rows\n    select:\n        id\n"
        + "".join(f"        v{i} = many(nope{i})\n" for i in range(count))
    )


def test_dropping_repeated_call_errors_grows_linearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analysis returns its diagnostics in source order, so one pass over the
    calls in source order places them all: each further call adds the same
    work, however many calls come before it."""
    analyzed: list[tuple[Script, tuple[Diagnostic, ...]]] = []
    monkeypatch.setattr(
        analyzer_module,
        "drop_repeated_call_diagnostics",
        lambda script, diagnostics: (
            analyzed.append((script, diagnostics)) or diagnostics
        ),
    )
    work: list[int] = []
    for count in (20, 40, 80):
        parsed = parse_source(_repeated_errors(count), path="m.pietto")
        assert parsed.ast is not None
        analyze(parsed.ast)
        script, diagnostics = analyzed.pop()
        drop = functools.partial(
            inline_module.drop_repeated_call_diagnostics, script, diagnostics
        )
        assert (len(diagnostics), len(drop())) == (32 * count, count)
        work.append(_module_lines(drop, sys.maxsize))
    assert work[2] - work[1] <= 2 * (work[1] - work[0])


def _typing_lines(depth: int, lets: str, value: str) -> int:
    """Typing work for one item that passes ``value`` through ``depth`` nested
    calls, ``lets`` being the relation's `let:` bindings."""

    source = (
        SHAPES
        + "def nl1(x: Int nullable) -> Int nullable: return x + 0\n"
        + "table t:\n    from rows\n"
        + (f"    let:\n{lets}" if lets else "")
        + "    select:\n        id\n        v = "
        + "nl1(" * depth
        + value
        + ")" * depth
        + "\n"
    )
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    assert analyze(parsed.ast).diagnostics == ()
    return _module_lines(
        functools.partial(analyze, parsed.ast), sys.maxsize, expressions_module
    )


@pytest.mark.parametrize(
    ("lets", "value", "factor"),
    [
        ("", "n", 1),
        ("        j = n\n", "j", 3 / 2),
        ("        k = null\n        j = coalesce(k, n)\n", "j", 4),
    ],
    ids=["field", "let_of_known_type", "let_reading_null"],
)
def test_checking_nested_arguments_grows_linearly(
    lets: str, value: str, factor: float
) -> None:
    """Each nested argument is checked once, as emission writes it, so twice
    the depth costs at most about twice the typing work; around a `let:` name
    of known type it costs about what the field it names does, and around one
    that reads a `let:` name bound to null a few times that."""
    work = _typing_lines(20, lets, value)
    assert _typing_lines(40, lets, value) <= work * 21 // 10
    assert work <= _typing_lines(20, "", "n") * factor


def _null_chain(length: int) -> tuple[int, list[tuple[str, int, int, str]]]:
    """Typing work and errors for `k0 = null`, each further `let:` name the
    one before passed through a nullable def, and the last read by a call
    whose parameter is `not null`."""

    source = (
        SHAPES
        + DEFS
        + "def same(x: Int nullable) -> Int nullable: return x\n"
        + "table t:\n    from rows\n    let:\n        k0 = null\n"
        + "".join(f"        k{i} = same(k{i - 1})\n" for i in range(1, length))
        + f"    select:\n        id\n        v = pos(same(k{length - 1}))\n"
    )
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    work = _module_lines(
        functools.partial(analyze, parsed.ast), sys.maxsize, expressions_module
    )
    return work, _errors(source)


def test_writing_a_chain_of_null_lets_grows_linearly() -> None:
    """Null fits every nullable parameter on its way, so the literal written
    for each name carries at most its first `not null` one, not every
    parameter before it: twice the chain costs at most about twice the
    typing work, and the error is still at the first call it does not fit."""
    work, errors = _null_chain(100)
    longer, longer_errors = _null_chain(200)
    assert longer <= work * 21 // 10
    assert [errors, longer_errors] == [
        [
            (
                "PIE-S2395",
                BODY_LINE + 6 + length,
                13,
                "Invalid argument for def pos at position 1 (x): "
                "expected Int not null, got null",
            )
        ]
        for length in (100, 200)
    ]


def _doubling(depth: int) -> int:
    """Typing work for a `let:` value ill-typed once the null it reads is
    written in, read twice by each of ``depth`` further names, the last read
    by twenty more, once a def argument makes the relation write them all."""

    source = (
        SHAPES
        + "def same(x: Int nullable) -> Int nullable: return x\n"
        + "table t:\n    from rows\n    let:\n        k = null\n"
        + "        s0 = upper(k) + 1\n"
        + "".join(f"        s{i} = s{i - 1} + s{i - 1}\n" for i in range(1, depth + 1))
        + "".join(f"        t{j} = s{depth} + {j}\n" for j in range(20))
        + "    select:\n        id\n        v = same(k)\n"
    )
    parsed = parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    assert analyze(parsed.ast).diagnostics == ()
    return _module_lines(
        functools.partial(analyze, parsed.ast), sys.maxsize, expressions_module
    )


def test_writing_lets_keeps_one_copy_of_each_error_they_read() -> None:
    """A written `let:` value keeps each error it reads once, however many
    paths lead to it, so twice the depth of names that each read the one
    before twice costs at most about twice the typing work."""
    assert _doubling(12) <= _doubling(6) * 21 // 10


def test_an_argument_used_twice_finds_its_reported_errors_by_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each item reports its argument's error as written once, although the
    body uses the argument twice, and finds the copy already reported by
    lookup, not by comparing it with every error reported before it: twice
    the items make at most about twice the comparisons."""

    def comparisons(items: int) -> int:
        source = (
            SHAPES
            + "def tw(x: Int nullable) -> Int nullable: return x + x\n"
            + "table t:\n    from rows\n    let:\n        k = null\n"
            + "        i = upper(k) + 1\n    select:\n        id\n"
            + "".join(f"        v{item} = tw(i)\n" for item in range(items))
        )
        parsed = parse_source(source, path="m.pietto")
        assert parsed.diagnostics == () and parsed.ast is not None
        count = 0
        compare = Diagnostic.__eq__

        def counted(self: Diagnostic, other: object) -> bool:
            nonlocal count
            count += 1
            return compare(self, other)

        with monkeypatch.context() as patch:
            patch.setattr(Diagnostic, "__eq__", counted)
            diagnostics = analyze(parsed.ast).diagnostics
        assert [
            (item.code, item.location.line, item.location.column)
            for item in diagnostics
        ] == [
            ("PIE-S2105", BODY_LINE + 6 + item, 16 + len(str(item)))
            for item in range(items)
        ]
        return count

    assert comparisons(200) <= comparisons(100) * 21 // 10


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
    assert _errors(source) == [
        ("PIE-S2103", BODY_LINE + 1, 17, f"Unknown function: {function}")
    ]


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
