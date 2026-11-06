"""Single-file top-level constants: declaration checks, typed reads and
`--set` values."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from _pietto_semantic_constants import CONSTANTS, FIRST, QUERY, SHAPE, parsed
from pietto.ast_nodes import LiteralExpr
from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.ir.model import RelationIR
from pietto.semantic import analyze
from pietto.semantic.constants import override_constants
from pietto.semantic.inline_functions import _tree_nodes


def _errors(source: str) -> list[tuple[str, int, int, str]]:
    result = analyze(parsed(SHAPE.format(dialect="postgres") + source))
    assert {item.severity for item in result.diagnostics} <= {Severity.ERROR}
    return [
        (
            item.code,
            item.location.line - FIRST + 1,
            item.location.column,
            item.message,
        )
        for item in result.diagnostics
    ]


def test_a_date_or_timestamp_read_is_typed_as_declared() -> None:
    source = SHAPE.format(dialect="postgres") + CONSTANTS + QUERY
    result = analyze(parsed(source))
    assert result.script is not None and result.script.constants == ()
    assert {
        node.value
        for node in _tree_nodes(result.script)
        if type(node) is LiteralExpr and isinstance(node.value, date)
    } == {date(2024, 1, 31), datetime(2024, 1, 31, 8, 30, 0, 250000)}
    lowered = build_ir(result.script, result.model)
    assert lowered.ir is not None
    (query,) = (
        item
        for item in lowered.ir.definitions
        if isinstance(item, RelationIR) and item.name == "q"
    )
    types = {
        item.name: item.type_ref.canonical_name
        for item in query.projections
        if item.type_ref is not None
    }
    assert (types["as_of"], types["stamped"], types["same_day"]) == (
        "Date",
        "Timestamp",
        "Bool",
    )


@pytest.mark.parametrize(
    ("setting", "message"),
    [
        (("missing", "1"), "--set missing: no top-level constant missing is declared"),
        (
            ("flag", "yes"),
            "--set flag: constant flag has type Bool; write True or False",
        ),
        (
            ("limit_n", "1.0"),
            "--set limit_n: constant limit_n has type Int; write an integer such as "
            "10 or -10",
        ),
        (
            ("lo", "2"),
            "--set lo: constant lo has type Float; write a number with a decimal point "
            "such as 1.5 or -1.5",
        ),
        (
            ("cutoff", "2024-02-30"),
            "--set cutoff: constant cutoff has type Date; write YYYY-MM-DD from "
            "1000-01-01 to 9999-12-31",
        ),
        (
            ("stamp", "2024-02-29T00:00:00"),
            "--set stamp: constant stamp has type Timestamp; write YYYY-MM-DD "
            "HH:MM:SS, with up to six fractional digits, from 1000-01-01 00:00:00 "
            "to 9999-12-31 23:59:59.499999",
        ),
        (
            ("label", "\udcff"),
            "--set label: constant label has type Text; write UTF-8 text",
        ),
    ],
    ids=["undeclared", "bool", "int", "float", "date", "timestamp", "text"],
)
def test_a_set_value_is_one_literal_of_a_declared_constant(
    setting: tuple[str, str], message: str
) -> None:
    script = parsed(SHAPE.format(dialect="postgres") + CONSTANTS + QUERY)

    with pytest.raises(ValueError) as raised:
        override_constants(script, (setting,))

    assert str(raised.value) == message


@pytest.mark.parametrize(
    ("value", "accepted"),
    [
        ("0999-12-31", False),
        ("1000-01-01", True),
        ("9999-12-31", True),
        ("2024-1-31", False),
        ("20240131", False),
    ],
)
def test_a_date_constant_is_one_civil_date(value: str, accepted: bool) -> None:
    errors = _errors(
        f'd: Date = "{value}"\n\nquery q:\n    from events\n    select:\n        id\n'
    )
    assert (errors == []) is accepted


@pytest.mark.parametrize(
    ("value", "accepted"),
    [
        ("9999-12-31 23:59:59.499999", True),
        ("9999-12-31 23:59:59.5", False),
        ("1000-01-01 00:00:00", True),
        ("2024-01-31", False),
        ("2024-01-31 08:30", False),
        ("2024-01-31 08:30:00.1234567", False),
    ],
)
def test_a_timestamp_constant_is_one_civil_timestamp(
    value: str, accepted: bool
) -> None:
    errors = _errors(
        f't: Timestamp = "{value}"\n\nquery q:\n    from events\n    select:\n        id\n'
    )
    assert (errors == []) is accepted


TYPE_ERROR = (
    "A constant is `Bool`, `Int`, `Float`, `Text`, `Date` or `Timestamp`, "
    "without `| None`."
)


def test_declarations_that_are_not_one_literal_of_a_constant_type() -> None:
    source = (
        "a: Decimal = 1\n\n"
        "b: Int | None = 1\n\n"
        'c: Date = date("2024-01-01")\n\n'
        "d: Float = Float(1)\n\n"
        "e: Float = 1\n\n"
        "f: Bool = None\n\n"
        "g: Int = 1 + 2\n\n"
        'h: Text = "x"\n\n'
        'h: Text = "y"\n\n'
        "query q:\n    from events\n    select:\n        id\n"
    )

    assert _errors(source) == [
        ("PIE-S2391", 1, 4, TYPE_ERROR),
        ("PIE-S2391", 3, 4, TYPE_ERROR),
        (
            "PIE-S2391",
            5,
            11,
            'Constant `c` takes one `Date` literal: a Text literal `"YYYY-MM-DD"` '
            "from 1000-01-01 to 9999-12-31.",
        ),
        (
            "PIE-S2391",
            7,
            12,
            "Constant `d` takes one `Float` literal: a number with a decimal point "
            "such as `1.5` or `-1.5`.",
        ),
        (
            "PIE-S2391",
            9,
            12,
            "Constant `e` takes one `Float` literal: a number with a decimal point "
            "such as `1.5` or `-1.5`.",
        ),
        (
            "PIE-S2391",
            11,
            11,
            "Constant `f` takes one `Bool` literal: `True` or `False`.",
        ),
        (
            "PIE-S2391",
            13,
            10,
            "Constant `g` takes one `Int` literal: an integer such as `10` or `-10`.",
        ),
        ("PIE-S2001", 17, 1, "Duplicate symbol name in constant namespace: h"),
    ]


def test_a_constant_name_has_one_meaning_and_reads_only_as_a_value() -> None:
    source = (
        "id: Int = 1\n\n"
        "n: Int = 2\n\n"
        "query q:\n    from events\n    group by n\n    select:\n        n\n"
        "        c = count()\n    order by c, n\n"
    )
    taken = (
        "Constant `id` is also declared as another name in this file; give the "
        "constant a name of its own."
    )
    key = "is no GROUP BY or ORDER BY key; a key reads a field or an output."

    assert _errors(source) == [
        ("PIE-S2391", 1, 1, taken),
        ("PIE-S2391", 7, 14, f"Constant `n` {key}"),
        (
            "PIE-S2391",
            9,
            9,
            "A SELECT item that reads only constant `n` needs its own name, such "
            "as `value = n`.",
        ),
        ("PIE-S2391", 11, 17, f"Constant `n` {key}"),
    ]
    # A def parameter, a let and a window are other names too.
    for other in (
        "def f(n: Int) -> Int: return n\n\n",
        "query r:\n    from events\n    let n = id\n    select:\n        m = n\n\n",
    ):
        assert _errors("n: Int = 2\n\n" + other)[0][3] == taken.replace("id", "n")


def test_a_constant_is_no_builtin_call_name_and_no_source_connector_argument() -> None:
    source = (
        'lower: Text = "x"\n\n'
        "Float: Float = 1.0\n\n"
        'table_name: Text = "events"\n\n'
        "source others: Event = postgres.table(table_name)\n\n"
        "query q:\n    from events\n    select:\n        v = lower(note)\n"
    )
    builtin = (
        "has the name of a built-in function; give the constant a name of its own."
    )

    assert _errors(source) == [
        ("PIE-S2391", 1, 1, f"Constant `lower` {builtin}"),
        ("PIE-S2391", 3, 1, f"Constant `Float` {builtin}"),
        (
            "PIE-S2391",
            7,
            39,
            "Constant `table_name` is no source connector argument; a source names "
            "what it reads with a literal written there.",
        ),
    ]
