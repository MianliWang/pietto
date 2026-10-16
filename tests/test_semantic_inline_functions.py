"""Pure inline ``def`` functions: definition checks, call checks and inlining.

A call is replaced by the def body with each argument in place of its
parameter before any call site is typed, so SQL for a program that calls a
def is byte-identical to the same program with the call written out by hand.
"""

from __future__ import annotations

import contextlib
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_sql_emission as emission
from pietto import cli
from pietto._inline_argument import InlinedArgument
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    FunctionDef,
    NameExpr,
    Script,
    TableDef,
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
                if item.compare and item.name != "span"
            ),
        )
    return value


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

    # The first use of an argument is the argument, carrying the parameter it
    # must fit; the expansion is located at the call; every other inlined node,
    # and every repeated use of an argument, is a distinct copy starting at the
    # call and checked through the first use.
    expression: Any = cast(TableDef, inlined.definitions[-1]).where_clause
    calls: Any = cast(TableDef, called.definitions[-1]).where_clause
    expression, calls = expression.expression, calls.expression
    assert type(calls) is BinaryExpr and type(calls.left) is CallExpr
    first = expression.left
    assert first.span == calls.left.span and first.argument_of == ()
    argument = first.left.left
    assert argument == calls.left.arguments[0]
    assert argument.argument_of == (
        InlinedArgument(
            call=calls.left.span,
            function="small",
            position=1,
            parameter="v",
            type_name="Int",
            nullable=False,
        ),
    )
    copy = first.right.left
    assert type(copy) is NameExpr and copy != argument and copy.argument_of == ()
    nodes = _expression_nodes(expression)
    assert len({id(node) for node in nodes}) == len(nodes)
    assert len(set(nodes)) == len(nodes)
    start = (calls.left.span.line, calls.left.span.column)
    assert (copy.span.line, copy.span.column) == start
    assert copy.span.end_line == start[0] and copy.span.end_column > start[1]


def _copy(value: object) -> object:
    """A structural copy of an AST in which every node is a new object."""

    if type(value) is tuple:
        return tuple(_copy(item) for item in value)
    if is_dataclass(value) and type(value).__module__ == "pietto.ast_nodes":
        return replace(
            cast(Any, value),
            **{item.name: _copy(getattr(value, item.name)) for item in fields(value)},
        )
    return value


def test_argument_checks_travel_with_the_inlined_script() -> None:
    """A copy of an inlined script, such as the one execution binds values
    into, keeps every argument check: no state outside the script holds it."""
    parsed = parse_source(
        SHAPES + DEFS + "table t:\n    from rows\n    where pos(n)\n"
        "    select:\n        id\n",
        path="m.pietto",
    ).ast
    assert parsed is not None
    inlined, diagnostics = inline_functions(parsed)
    assert diagnostics == ()
    copied = _copy(inlined)
    assert copied == inlined and copied is not inlined
    for script in (inlined, copied):
        assert [
            (d.code, d.location.line, d.location.column, d.message)
            for d in analyze(cast(Script, script)).diagnostics
        ] == [
            (
                "PIE-S2395",
                BODY_LINE + 2,
                11,
                "Invalid argument for def pos at position 1 (x): expected Int "
                "not null, got Int nullable",
            )
        ]


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
    # The error inside the argument is reported once per use: at the copy,
    # which starts at the call, and at the argument itself.
    assert _errors(source) == [
        ("PIE-S2103", BODY_LINE + 1, column, f"Unknown function: {function}")
        for column in (11, 17)
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


def _run(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(argv)
    return code, out.getvalue()


SINGLE_FILE = {
    "where_two_defs": (
        "def reachable(email: Text nullable, coupon: Text nullable) -> Bool nullable: "
        'return email like "%@%" and coupon is null\n'
        "def positive(v: Int not null) -> Bool nullable: return v > 0\n"
        "table t:\n    from rows\n    where positive(id) and reachable(note, note)\n"
        "    select:\n        id\n",
        "table t:\n    from rows\n"
        '    where (id > 0) and (note like "%@%" and note is null)\n'
        "    select:\n        id\n",
    ),
    "repeated_parameter_and_call": (
        "def small(v: Int not null) -> Bool nullable: return v > 0 and v < 9\n"
        "def clean(s: Text not null) -> Text not null: return lower(trim(s))\n"
        "table t:\n    from rows\n    let: c = clean(text)\n"
        "    where small(id) and clean(text) != clean(text)\n"
        "    select:\n        id\n        cc = c\n        d = clean(text)\n"
        "    order by: id desc\n",
        "table t:\n    from rows\n    let: c = (lower(trim(text)))\n"
        "    where (id > 0 and id < 9) and (lower(trim(text))) != (lower(trim(text)))\n"
        "    select:\n        id\n        cc = c\n        d = (lower(trim(text)))\n"
        "    order by: id desc\n",
    ),
    "nested_defs": (
        "def tag(s: Text not null) -> Text not null: return upper(s)\n"
        "def label(s: Text not null, v: Int not null) -> Text not null: "
        'return tag(s) if v > 0 else "none"\n'
        "table t:\n    from rows\n    select:\n        id\n"
        "        l = label(text, id)\n",
        "table t:\n    from rows\n    select:\n        id\n"
        '        l = ((upper(text)) if id > 0 else "none")\n',
    ),
}


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
@pytest.mark.parametrize(("called", "written"), SINGLE_FILE.values(), ids=SINGLE_FILE)
def test_single_file_sql_is_byte_identical_to_the_call_written_out(
    tmp_path: Path, dialect: str, called: str, written: str
) -> None:
    shapes = SHAPES.replace("postgres.table", f"{dialect}.table")
    outputs = []
    for name, relation in (("called", called), ("written", written)):
        path = tmp_path / f"{name}.pietto"
        path.write_text(shapes + relation, encoding="utf-8")
        code, sql = _run(["emit-sql", str(path), "--dialect", dialect])
        assert code == 0
        outputs.append(sql)
    assert outputs[0] == outputs[1]
    assert "SELECT" in outputs[0]


def test_single_file_explain_lists_no_def(tmp_path: Path) -> None:
    called, written = SINGLE_FILE["nested_defs"]
    documents = []
    for name, relation in (("called", called), ("written", written)):
        path = tmp_path / f"{name}.pietto"
        path.write_text(SHAPES + relation, encoding="utf-8")
        code, document = _run(["explain", str(path), "--format", "json"])
        assert code == 0
        documents.append(json.loads(document)["metadata"]["definitions"])
    assert (
        [(d["name"], d["kind"]) for d in documents[0]]
        == [(d["name"], d["kind"]) for d in documents[1]]
        == [("Row", "shape"), ("rows", "source"), ("t", "table")]
    )


def _project(root: Path, files: dict[str, str], schema_version: int = 2) -> Path:
    root.mkdir()
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return root


def _project_errors(root: Path) -> list[tuple[str, str, int, int, str]]:
    code, document = _run(["check", "--project", str(root), "--format", "json"])
    diagnostics = json.loads(document)["diagnostics"]
    assert code == (1 if diagnostics else 0)
    return [
        (
            d["code"],
            d["location"]["path"],
            d["location"]["line"],
            d["location"]["column"],
            d["message"],
        )
        for d in diagnostics
    ]


def test_project_defs_are_module_local_and_not_exported(tmp_path: Path) -> None:
    local = SHAPES + DEFS + "export:\n    source rows\n"
    caller = (
        'import "a.pietto":\n    source rows\n'
        "table t:\n    from rows\n    where pos(id)\n    select:\n        id\n"
    )
    used_here = (
        local + "table u:\n    from rows\n    where pos(id)\n    select:\n        id\n"
    )
    assert _project_errors(_project(tmp_path / "ok", {"a.pietto": used_here})) == []
    assert _project_errors(
        _project(tmp_path / "other", {"a.pietto": local, "b.pietto": caller})
    ) == [("PIE-S2103", "b.pietto", 5, 11, "Unknown function: pos")]
    exported = _project(
        tmp_path / "export", {"a.pietto": DEFS + "export:\n    table pos\n"}
    )
    assert _project_errors(exported) == [
        ("PIE-S2704", "a.pietto", 4, 11, "Unknown export binding: table pos")
    ]
    keyword = _project(
        tmp_path / "keyword", {"a.pietto": DEFS + "export:\n    def pos\n"}
    )
    assert [error[:4] for error in _project_errors(keyword)] == [
        ("PIE-P1000", "a.pietto", 4, 5)
    ]


def test_project_modes_without_modules_keep_def_gated(tmp_path: Path) -> None:
    root = _project(tmp_path / "flat", {"a.pietto": SHAPES + DEFS}, schema_version=1)
    assert _project_errors(root) == [
        (
            "PIE-S2379",
            "a.pietto",
            line,
            1,
            "Inline `def` functions are available only in single files and "
            "EXPLICIT_MODULES projects (schema version 2).",
        )
        for line in (8, 9)
    ]


def test_project_checks_header_and_captured_arguments(tmp_path: Path) -> None:
    source = (
        SHAPES
        + DEFS
        + (
            "query q(k: Int not null, m: Int nullable):\n    from rows\n"
            "    where pos(k) and pos(m)\n    select:\n        id\n"
            "query c:\n    let l:\n        capture rows\n        from tags\n"
            "        where pos(rows.n)\n        select:\n            id\n"
            "    from rows\n    where exists l\n    select:\n        id\n"
            'shape Tag:\n    id: Int not null\nsource tags: Tag is postgres.table("tags")\n'
        )
    )
    assert _project_errors(_project(tmp_path / "p", {"a.pietto": source})) == [
        (
            "PIE-S2395",
            "a.pietto",
            BODY_LINE + 2,
            22,
            "Invalid argument for def "
            "pos at position 1 (x): expected Int not null, got Int nullable",
        ),
        (
            "PIE-S2395",
            "a.pietto",
            BODY_LINE + 9,
            15,
            "Invalid argument for def "
            "pos at position 1 (x): expected Int not null, got Int nullable",
        ),
    ]


PROJECT = {
    "row_body": (
        "T_row_direct",
        "table_preserve",
        "table",
        "def small(n: Int not null) -> Bool nullable: return n > 0 and n < 1000\n"
        "def both(a: Int not null, b: Int not null) -> Bool nullable: "
        "return small(a) and small(b)\n"
        "def label(t: Text not null, f: Bool nullable) -> Text not null: "
        'return "on" if f is null else lower(t)\n'
        "def next_of(n: Int not null) -> Int nullable: return n + 1\n",
        [
            ("bumped = id + 1", "bumped = next_of(id)"),
            ("where id > 0", "where both(id, id) and small(id)"),
            ("positive = id > 0", "positive = label(text, flag) == label(text, flag)"),
        ],
        [
            ("bumped = id + 1", "bumped = (id + 1)"),
            (
                "where id > 0",
                "where ((id > 0 and id < 1000) and (id > 0 and id < 1000)) and "
                "(id > 0 and id < 1000)",
            ),
            (
                "positive = id > 0",
                'positive = ("on" if flag is null else lower(text)) == '
                '("on" if flag is null else lower(text))',
            ),
        ],
    ),
    "bound_literals": (
        "T_row_direct",
        "query_bind",
        "query",
        "def small(n: Int not null) -> Bool nullable: return n > 0 and n < 1000\n",
        [("where id > 0", "where small(id) and small(id)")],
        [("where id > 0", "where (id > 0 and id < 1000) and (id > 0 and id < 1000)")],
    ),
    "grouped_let_key": (
        "Y_aggregate_computed",
        "let_key",
        "query",
        "def bucket_of(k: Int nullable) -> Int not null: return 1 if k > 1 else 0\n",
        [("bucket = 1 if key > 1 else 0", "bucket = bucket_of(key)")],
        [("bucket = 1 if key > 1 else 0", "bucket = (1 if key > 1 else 0)")],
    ),
    "satisfying": (
        "Y_aggregate_satisfying",
        "retained",
        "query",
        "def small(t: Int not null) -> Bool nullable: return t < 2\n",
        [("total < 2 and lo > 5", "small(total) and lo > 5")],
        [("total < 2 and lo > 5", "(total < 2) and lo > 5")],
    ),
    "qualify": (
        "A_window_qualify",
        "selected",
        "query",
        "def top(n: Int not null) -> Bool nullable: return n <= 2\n",
        [("numbered <= 2", "top(numbered)")],
        [("numbered <= 2", "(numbered <= 2)")],
    ),
    "join_on": (
        "W_join_values",
        "left_marker",
        "query",
        "def same(a: Int not null, b: Int not null) -> Bool nullable: return a == b\n",
        [("on rows.id == r.pid", "on same(rows.id, r.pid)")],
        [("on rows.id == r.pid", "on (rows.id == r.pid)")],
    ),
}
COMPARED = ("sql", "columns", "fixed_values", "parameter_uses", "requirements")


@pytest.mark.parametrize("target", ["postgres", "mysql"])
@pytest.mark.parametrize(
    ("case", "variant", "kind", "defs", "called", "written"),
    PROJECT.values(),
    ids=PROJECT,
)
def test_project_sql_is_byte_identical_to_the_call_written_out(
    tmp_path: Path,
    target: str,
    case: str,
    variant: str,
    kind: str,
    defs: str,
    called: list[tuple[str, str]],
    written: list[tuple[str, str]],
) -> None:
    item = emission.fixture(target, case, variant)
    documents = []
    for name, edits, extra in (("called", called, defs), ("written", written, "")):
        source = item["source"]
        for old, new in edits:
            assert source.count(old) == 1
            source = source.replace(old, new)
        root = _project(tmp_path / name, {"main.pietto": source + extra})
        (root / "contract.json").write_text(item["contract"], encoding="utf-8")
        argv = [
            "emit-sql",
            "--project",
            str(root),
            "--module",
            "main.pietto",
            "--kind",
            kind,
            "--name",
            "result",
            "--dialect",
            target,
            "--emission-contract",
            "contract.json",
        ]
        if item["policy"] == "bind_safe_literals":
            argv += ["--literal-policy", "bind-safe"]
        code, document = _run(argv)
        assert code == 0
        documents.append(json.loads(document))
    assert documents[0]["status"] == documents[1]["status"] == "VERIFIED"
    for key in COMPARED:
        assert documents[0][key] == documents[1][key], key
