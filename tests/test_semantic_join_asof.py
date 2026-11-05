"""The backward asof JOIN: admitted forms and every refused variant.

An `asof left join` or `asof inner join` keeps, for each earlier row, the
latest joined row whose keys match and whose time is at or before the
earlier row's; a declared unique within the keys and the time proves at
most one. Each refused variant is one diagnostic with its hint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from _pietto_semantic_join_asof import (
    CANONICAL,
    JOIN_LINE,
    KEY,
    SHAPES,
    TIME,
    asof_query,
)
from pietto._asof_join import (
    ASOF_KIND_MESSAGE,
    ASOF_SOURCE_MESSAGE,
    AsofForm,
    asof_form,
    lower_latest_rows,
)
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.ast_nodes import (
    AnyExpr,
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    QueryDef,
    Script,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode

_OTHER = (
    "An asof `on` takes only field `==` keys and one time test; filter the "
    "joined rows with a view source, compute values in an earlier query."
)
_KIND = "ASOF JOIN is `asof left join` or `asof inner join`."
_FORWARD = (
    "asof finds the latest earlier-or-equal row only; the next later row is "
    "not available."
)
_STRICT = (
    "Write `>=`: a row at the same moment matches; excluding it is not "
    "available; for the previous row of one input use `lag(...)`."
)
_LEFT_EXTRA = (
    "An asof `on` takes one time test; to keep every orders row, test the "
    "chosen row in select instead: `x = price.<field> if {test} else None`."
)
_TYPES = (
    "The time test needs Date on both sides or Timestamp on both sides; got {} and {}."
)
_TIE = "Several rows of price may be the latest for one orders row; Pietto does not pick one. "
_ONLY_ORDERS = "select order_id = orders.id"
_BOTH = "select order_id = orders.id, c = price.amount_cents"


def _diagnostics(source: str) -> list[tuple[int, str, str]]:
    parsed = parse_source(source, path="asof.pietto")
    found = (
        parsed.diagnostics if parsed.ast is None else analyze(parsed.ast).diagnostics
    )
    return [(item.location.line, item.code, item.message) for item in found]


@pytest.mark.parametrize("kind", ["left", "inner"])
@pytest.mark.parametrize(
    ("join", "let"),
    [
        (f"{KEY} and {TIME}", "let price = prices"),
        (f"{KEY} and orders.region == price.region and {TIME}", "let price = prices3"),
        (f"{KEY} and orders.ordered_on >= price.valid_on", "let price = prices_on"),
        (TIME.replace("price.", "rate."), "let rate = rates"),
    ],
    ids=["one_key", "two_keys", "date", "zero_keys"],
)
def test_admitted_asof_joins_check_clean(kind: str, join: str, let: str) -> None:
    binding = let.split()[1]
    source = asof_query(
        f"asof {kind} join {binding} on {join}",
        let=let,
        select=_ONLY_ORDERS,
    )
    assert _diagnostics(source) == []
    assert _diagnostics(CANONICAL) == []


_REFUSED = {
    "asof_right": ("asof right join price on {KEY} and {TIME}", "PIE-S2336", _KIND),
    "asof_full": ("asof full join price on {KEY} and {TIME}", "PIE-S2336", _KIND),
    "asof_cross": ("asof cross join price", "PIE-S2336", _KIND),
    "asof_semi": ("asof semi join price on {KEY} and {TIME}", "PIE-S2336", _KIND),
    "asof_anti": ("asof anti join price on {KEY} and {TIME}", "PIE-S2336", _KIND),
    "missing_on": (
        "asof left join price",
        "PIE-S2335",
        "JOIN price: write `on` with the keys, then one time test: "
        "`on orders.k == price.k and orders.t >= price.t`",
    ),
    "no_time": (
        "asof left join price on {KEY}",
        "PIE-S2336",
        "Add one time test last: `and orders.t >= price.t`.",
    ),
    "strict": (
        "asof left join price on {KEY} and orders.ordered_at > price.valid_from",
        "PIE-S2336",
        _STRICT,
    ),
    "strict_reversed": (
        "asof left join price on {KEY} and price.valid_from < orders.ordered_at",
        "PIE-S2336",
        _STRICT,
    ),
    "reversed_time": (
        "asof left join price on {KEY} and price.valid_from <= orders.ordered_at",
        "PIE-S2336",
        "Write the earlier input first in each test: "
        "`orders.ordered_at >= price.valid_from`.",
    ),
    "reversed_key": (
        "asof left join price on price.product_id == orders.product_id and {TIME}",
        "PIE-S2336",
        "Write the earlier input first in each test: "
        "`orders.product_id == price.product_id`.",
    ),
    "forward_le": (
        "asof left join price on {KEY} and orders.ordered_at <= price.valid_from",
        "PIE-S2336",
        _FORWARD,
    ),
    "forward_lt": (
        "asof left join price on {KEY} and orders.ordered_at < price.valid_from",
        "PIE-S2336",
        _FORWARD,
    ),
    "forward_reversed_ge": (
        "asof left join price on {KEY} and price.valid_from >= orders.ordered_at",
        "PIE-S2336",
        _FORWARD,
    ),
    "forward_reversed_gt": (
        "asof left join price on {KEY} and price.valid_from > orders.ordered_at",
        "PIE-S2336",
        _FORWARD,
    ),
    "time_first": (
        "asof left join price on {TIME} and {KEY}",
        "PIE-S2336",
        "Write the keys first and the one time test last.",
    ),
    "key_twice": (
        "asof left join price on {KEY} and {KEY} and {TIME}",
        "PIE-S2336",
        "Match each key once: remove the repeated "
        "`orders.product_id == price.product_id`.",
    ),
    "second_time_inner": (
        "asof inner join price on {KEY} and {TIME} and "
        "price.valid_from >= orders.week_start",
        "PIE-S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where price.valid_from >= orders.week_start`.",
    ),
    "second_time_left": (
        "asof left join price on {KEY} and {TIME} and "
        "price.valid_from >= orders.week_start",
        "PIE-S2336",
        _LEFT_EXTRA.format(test="price.valid_from >= orders.week_start"),
    ),
    "chain": (
        "asof left join price on {KEY} and "
        "orders.ordered_at >= price.valid_from >= orders.week_start",
        "PIE-S2336",
        _LEFT_EXTRA.format(test="price.valid_from >= orders.week_start"),
    ),
    "lower_before_inner": (
        "asof inner join price on {KEY} and orders.week_start <= price.valid_from "
        "and {TIME}",
        "PIE-S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where orders.week_start <= price.valid_from`.",
    ),
    "lower_before_left": (
        "asof left join price on {KEY} and orders.week_start <= price.valid_from "
        "and {TIME}",
        "PIE-S2336",
        _LEFT_EXTRA.format(test="orders.week_start <= price.valid_from"),
    ),
    "chain_le_left": (
        "asof left join price on {KEY} and "
        "orders.week_start <= price.valid_from <= orders.ordered_at",
        "PIE-S2336",
        _LEFT_EXTRA.format(test="orders.week_start <= price.valid_from").replace(
            "test; ", "test; keep `orders.ordered_at >= price.valid_from` in `on`; "
        ),
    ),
    "chain_le_inner": (
        "asof inner join price on {KEY} and "
        "orders.week_start <= price.valid_from <= orders.ordered_at",
        "PIE-S2336",
        "An asof `on` takes one time test; keep `orders.ordered_at >= "
        "price.valid_from` in `on`; test the chosen row after the JOIN instead: "
        "`where orders.week_start <= price.valid_from`.",
    ),
    "chain_lt_le_left": (
        "asof left join price on {KEY} and "
        "orders.week_start < price.valid_from <= orders.ordered_at",
        "PIE-S2336",
        _LEFT_EXTRA.format(test="orders.week_start < price.valid_from").replace(
            "test; ", "test; keep `orders.ordered_at >= price.valid_from` in `on`; "
        ),
    ),
    "chain_lt_le_inner": (
        "asof inner join price on {KEY} and "
        "orders.week_start < price.valid_from <= orders.ordered_at",
        "PIE-S2336",
        "An asof `on` takes one time test; keep `orders.ordered_at >= "
        "price.valid_from` in `on`; test the chosen row after the JOIN instead: "
        "`where orders.week_start < price.valid_from`.",
    ),
    "arithmetic": (
        "asof inner join price on {KEY} and orders.amount >= price.amount_cents + 1",
        "PIE-S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where orders.amount >= price.amount_cents + 1`.",
    ),
    "validity_range": (
        "asof left join price on {KEY} and {TIME} and "
        "orders.ordered_at < price.valid_to",
        "PIE-S2336",
        "For a validity range, use `left join price on` with both tests.",
    ),
    "or": ("asof left join price on {KEY} or {TIME}", "PIE-S2336", _OTHER),
    # A field compared with a value that reads no field is a filter.
    "joined_filter": (
        "asof inner join price on {KEY} and {TIME} and price.amount_cents > 0",
        "PIE-S2336",
        _OTHER,
    ),
    "earlier_filter": (
        "asof left join price on {KEY} and orders.amount >= 1 and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    # Only arithmetic is time arithmetic; a call or sign computes a value.
    "computed_value": (
        "asof inner join price on {KEY} and {TIME} and "
        "orders.amount >= abs(price.amount_cents)",
        "PIE-S2336",
        _OTHER,
    ),
    "not_equal": (
        "asof left join price on orders.region != price.region and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "literal": (
        "asof left join price on price.amount_cents == 3 and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "same_input": (
        "asof left join price on orders.product_id == orders.amount and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "call": (
        "asof left join price on abs(orders.product_id) == price.product_id and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "relationship_call": (
        "asof left join price on order_price(orders, price) and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "in_list": (
        'asof left join price on {KEY} and price.region in ("a", "b") and {TIME}',
        "PIE-S2336",
        _OTHER,
    ),
    "is_none": (
        "asof left join price on price.region is None and {TIME}",
        "PIE-S2336",
        _OTHER,
    ),
    "bare": (
        "asof left join price on {KEY} and ordered_at >= price.valid_from",
        "PIE-S2336",
        "Qualify each field with its input.",
    ),
    "date_and_timestamp": (
        "asof left join price on {KEY} and orders.ordered_on >= price.valid_from",
        "PIE-S2336",
        _TYPES.format("Date", "Timestamp"),
    ),
    "int_time": (
        "asof left join price on {KEY} and orders.amount >= price.amount_cents",
        "PIE-S2336",
        _TYPES.format("Int", "Int"),
    ),
    "text_time": (
        "asof left join price on {KEY} and orders.region >= price.region",
        "PIE-S2336",
        _TYPES.format("Text", "Text"),
    ),
    "float_key": (
        "asof left join price on orders.score == price.score and {TIME}",
        "PIE-S2336",
        "An asof key cannot be Float.",
    ),
    # Precedence: a conjunct with its own error gets no form message.
    "cross_family": (
        "asof left join price on {KEY} and orders.region >= price.valid_from",
        "PIE-S2105",
        "Invalid operands for operator >=: expected comparable operands",
    ),
    "unknown_earlier": (
        "asof left join price on orders.nope == price.product_id and {TIME}",
        "PIE-S2335",
        "JOIN ON reference is unknown: orders.nope",
    ),
    "unknown_joined": (
        "asof left join price on {KEY} and orders.ordered_at >= price.nope",
        "PIE-S2335",
        "JOIN ON reference is unknown: price.nope",
    ),
    "kind_before_form": (
        "asof right join price on {KEY} and orders.ordered_at > price.valid_from",
        "PIE-S2336",
        _KIND,
    ),
}


@pytest.mark.parametrize("name", sorted(_REFUSED))
def test_each_refused_asof_form_has_one_diagnostic_and_its_hint(name: str) -> None:
    join, code, message = _REFUSED[name]
    source = asof_query(
        join.format(KEY=KEY, TIME=TIME),
        select=_ONLY_ORDERS
        if "semi" in join or "anti" in join
        else ("select order_id = orders.id, c = price.amount_cents"),
    )
    found = _diagnostics(source)
    assert [(code, message)] == [(item[1], item[2]) for item in found]
    assert found[0][0] == JOIN_LINE


_UNIQUE = (
    (
        "let price = price_table",
        "asof JOIN joins only a source: one latest row is proved by the "
        "source shape's unique(...).",
    ),
    (
        "let price = prices_none",
        _TIE + "If the data has one row per product_id and valid_from, "
        "declare `price_key = unique(product_id, valid_from)` in shape PriceNone.",
    ),
    (
        "let price = prices_id",
        _TIE + "If the data has one row per product_id and valid_from, "
        "declare `price_key = unique(product_id, valid_from)` in shape PriceId.",
    ),
    (
        "let price = prices_two",
        _TIE + "PriceTwo.b_key = unique(product_id, region, valid_from) has "
        "region, which `on` does not match: add `orders.region == price.region`.",
    ),
    (
        "let price = prices3",
        _TIE + "Price3.p3_key = unique(product_id, region, valid_from) has "
        "region, which `on` does not match: add `orders.region == price.region`.",
    ),
    (
        "let price = prices_on",
        _TIE + "PriceOn.on_key = unique(product_id, valid_on) has valid_on, "
        "which `on` does not match: match price.valid_on in `on`.",
    ),
)
_UNIQUE_IDS = (
    "table",
    "no_unique",
    "unique_id",
    "surrogate_first",
    "unique_outside_on",
    "unique_unmatched",
)


@pytest.mark.parametrize(("let", "message"), _UNIQUE, ids=_UNIQUE_IDS)
def test_one_latest_row_needs_a_source_unique_within_keys_and_time(
    let: str, message: str
) -> None:
    source = asof_query(
        f"asof left join price on {KEY} and {TIME}", let=let, select=_ONLY_ORDERS
    )
    assert _diagnostics(source) == [(JOIN_LINE, "PIE-S2386", message)]


@pytest.mark.parametrize(
    ("on", "let", "shape", "declare"),
    [
        (
            f"{KEY} and {TIME}",
            "let price = prices_keyed",
            "PriceKeyed",
            "price_key_2 = unique(product_id, valid_from)",
        ),
        (
            f"{KEY} and orders.amount == price.product_id and {TIME}",
            "let price = prices_none",
            "PriceNone",
            "price_key = unique(product_id, valid_from)",
        ),
    ],
    ids=["name_taken", "field_twice"],
)
def test_the_unique_to_declare_is_one_the_shape_admits(
    tmp_path: Path, on: str, let: str, shape: str, declare: str
) -> None:
    """A name the shape does not declare, each field once: pasted into the
    shape, the declaration checks clean."""

    source = asof_query(f"asof left join price on {on}", let=let, select=_ONLY_ORDERS)
    message = (
        _TIE + "If the data has one row per product_id and valid_from, declare "
        f"`{declare}` in shape {shape}."
    )
    assert _diagnostics(source) == [(JOIN_LINE, "PIE-S2386", message)]
    assert _project_diagnostics(tmp_path / "p", source) == [("PIE-S2386", message)]
    pasted = source.replace(f"shape {shape}:\n", f"shape {shape}:\n    {declare}\n")
    assert _diagnostics(pasted) == []


@pytest.mark.parametrize(
    ("on", "test"),
    [
        ("orders.amount == price.score and {TIME}", "orders.amount == price.score"),
        (
            "orders.score == price.amount_cents and {TIME}",
            "orders.score == price.amount_cents",
        ),
        (
            "{KEY} and orders.amount >= price.amount_cents",
            "orders.amount >= price.amount_cents",
        ),
    ],
    ids=["float_joined_key", "float_earlier_key", "int_time"],
)
def test_a_type_refusal_of_an_asof_test_is_at_the_whole_test(
    tmp_path: Path, on: str, test: str
) -> None:
    source = asof_query(
        "asof left join price on " + on.format(KEY=KEY, TIME=TIME), select=_ONLY_ORDERS
    )
    column = source.splitlines()[JOIN_LINE - 1].index(test) + 1
    expected = [("PIE-S2336", (JOIN_LINE, column, JOIN_LINE, column + len(test)))]
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None
    for found in (
        analyze(parsed.ast).diagnostics,
        _project_found(tmp_path / "p", source),
    ):
        assert [
            (
                item.code,
                (
                    item.location.line,
                    item.location.column,
                    item.location.end_line,
                    item.location.end_column,
                ),
            )
            for item in found
        ] == expected


_DEFS = (
    "def at_or_before(t: Timestamp, v: Timestamp) -> Bool: return t >= v\n"
    "def back(v: Timestamp, t: Timestamp) -> Bool: return v <= t\n"
    "def same_key(a: Int, b: Int) -> Bool: return a == b\n"
    "def same(a: Int) -> Int: return a\n"
    "def within(lo: Timestamp, t: Timestamp, hi: Timestamp) -> Bool: "
    "return lo <= t <= hi\n"
    "def band(x: Int) -> Bool: return 1 <= x + 0 <= 3\n"
    "def holds(b: Bool | None) -> Bool | None: return b\n"
)


@pytest.mark.parametrize(
    "on",
    [
        "{KEY} and at_or_before(orders.ordered_at, price.valid_from)",
        "{KEY} and back(price.valid_from, orders.ordered_at)",
        "same_key(orders.product_id, price.product_id) and {TIME}",
        "same(orders.product_id) == price.product_id and {TIME}",
        "{KEY} and within(orders.ordered_at, price.valid_from, orders.ordered_at)",
        "{KEY} and {TIME} and band(price.amount_cents)",
        "holds({KEY}) and {TIME}",
        "{KEY} and {TIME} and holds(orders.week_start <= price.valid_from "
        "<= orders.ordered_at)",
    ],
    ids=[
        "time",
        "reversed_time",
        "key",
        "key_operand",
        "chain",
        "chain_of_body_values",
        "argument_key",
        "argument_chain",
    ],
)
def test_a_def_call_in_an_asof_on_is_no_test_of_its_form(
    tmp_path: Path, on: str
) -> None:
    """The fixed form is written in `on` itself; no rewrite of a def body."""

    source = _DEFS + asof_query(
        "asof left join price on " + on.format(KEY=KEY, TIME=TIME), select=_BOTH
    )
    line = JOIN_LINE + _DEFS.count("\n")
    assert _diagnostics(source) == [(line, "PIE-S2336", _OTHER)]
    assert _project_diagnostics(tmp_path / "p", source) == [("PIE-S2336", _OTHER)]


def test_one_asof_join_per_query_and_asof_stays_a_name() -> None:
    source = asof_query(
        f"asof left join price on {KEY} and {TIME}",
        after="    let p2 = prices\n    asof inner join p2 on orders.product_id "
        "== p2.product_id and orders.ordered_at >= p2.valid_from\n",
        select=_ONLY_ORDERS,
    )
    assert _diagnostics(source) == [
        (
            JOIN_LINE + 2,
            "PIE-S2336",
            "One asof JOIN per query: move the first into its own query and `from` it.",
        )
    ]
    named = asof_query("let asof = prices", select="select asof = orders.id")
    assert _diagnostics(named) == []


@pytest.mark.parametrize("mode", list(CheckMode))
def test_every_asof_refusal_is_an_error_in_every_check_mode(mode: CheckMode) -> None:
    source = asof_query(
        f"asof left join price on {KEY} and orders.ordered_at > price.valid_from"
    )
    parsed = parse_source(source, path="asof.pietto")
    assert parsed.ast is not None
    found = analyze(parsed.ast, mode_override=mode).diagnostics
    assert [(item.code, item.severity) for item in found] == [
        ("PIE-S2336", Severity.ERROR)
    ]


def _project_found(root: Path, source: str) -> tuple[Diagnostic, ...]:
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")
    return build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    ).diagnostics


def _project_diagnostics(root: Path, source: str) -> list[tuple[str, str]]:
    return [(item.code, item.message) for item in _project_found(root, source)]


def test_a_project_admits_the_asof_join_example(tmp_path: Path) -> None:
    assert _project_diagnostics(tmp_path / "p", CANONICAL) == []


@pytest.mark.parametrize(
    "name",
    [
        *sorted(_REFUSED),
        *(f"unique_{item}" for item in _UNIQUE_IDS),
        "second_asof",
        "shadow_after",
    ],
)
def test_a_project_refuses_each_asof_form_as_a_single_file_does(
    tmp_path: Path, name: str
) -> None:
    if name.startswith("unique_"):
        let = _UNIQUE[_UNIQUE_IDS.index(name[7:])][0]
        source = asof_query(
            f"asof left join price on {KEY} and {TIME}", let=let, select=_ONLY_ORDERS
        )
    elif name == "shadow_after":
        # A later `let` that shadows a relation names no asof target.
        source = asof_query(
            f"asof left join price on {KEY} and {TIME}",
            after="    let c = price.amount_cents\n    let prices = c\n",
            select="select order_id = orders.id, x = prices",
        )
    elif name == "second_asof":
        source = asof_query(
            f"asof left join price on {KEY} and {TIME}",
            after="    let p2 = prices\n    asof inner join p2 on orders.product_id "
            "== p2.product_id and orders.ordered_at >= p2.valid_from\n",
            select=_ONLY_ORDERS,
        )
    else:
        join = _REFUSED[name][0].format(KEY=KEY, TIME=TIME)
        source = asof_query(
            join,
            select=_ONLY_ORDERS if "semi" in join or "anti" in join else _BOTH,
        )
    single = [(code, message) for _, code, message in _diagnostics(source)]
    assert single
    if name == "missing_on":
        # A project reports every JOIN without `on` as its relation's PIE-S2333.
        single = [
            (
                "PIE-S2333",
                f"Project relation semantic completion is unavailable: q ({message})",
            )
            for _, message in single
        ]
    assert _project_diagnostics(tmp_path / "p", source) == single


_ON = "{e}.product_id == price.product_id and {e}.ordered_at >= price.valid_from"
_LET_BLOCK = "    let price:\n        {capture}from prices\n{where}        select:\n"
_LET_BLOCK += "            product_id\n            valid_from\n"
_FLAT = "    from orders\n    let price = prices\n    asof left join price on "
_FLAT += _ON.format(e="orders") + "\n"
# Where existence normalization takes no any(...) in the JOIN's `on`.
_UNLOWERED = {
    "set_earlier": (
        "    let both:\n        union all orders, orders\n    from both\n"
        "    let price = prices\n    asof left join price on "
        + _ON.format(e="both")
        + "\n    select order_id = both.id\n"
    ),
    "values_earlier": (
        "    let seed:\n        values(id: Int, product_id: Int, ordered_at: "
        "Timestamp):\n            1, 2, None\n    from seed\n"
        "    let price = prices\n    asof left join price on "
        + _ON.format(e="seed")
        + "\n    select order_id = seed.id\n"
    ),
    "table_function": (
        "    from generate_series(1, 31, 1) as n\n    let rate = rates\n"
        "    asof left join rate on n.n >= rate.valid_from\n    select x = n.n\n"
    ),
    "target_let_block": (
        _LET_BLOCK.format(capture="", where="")
        + "    from orders\n    asof left join price on "
        + _ON.format(e="orders")
        + "\n    select order_id = orders.id\n"
    ),
    "target_capture_let": (
        _LET_BLOCK.format(
            capture="capture orders\n        ",
            where="        where prices.product_id == orders.product_id\n",
        )
        + "    from orders\n    asof left join price on "
        + _ON.format(e="orders")
        + "\n    select order_id = orders.id\n"
    ),
    "in_let_body": (
        "    let inner_q:\n"
        + _FLAT.replace("    ", "        ")
        + "        select:\n            id = orders.id\n"
        "    from inner_q\n    select i = inner_q.id\n"
    ),
    "beside_a_let": (
        "    let other:\n        from prices\n        select:\n"
        "            product_id\n"
        + _FLAT
        + "    where orders.product_id in other\n    select order_id = orders.id\n"
    ),
}
_NOT_YET = ("PIE-S2336", "asof JOIN is not available in projects yet.")
_SOURCE_ONLY = ("PIE-S2386", ASOF_SOURCE_MESSAGE)
_VALUES_TYPE = (
    "PIE-S2361",
    "VALUES column type must be Bool, Int, Float or Text, optionally followed by "
    "'| None'.",
)
_CROSS = ("PIE-S2105", "Invalid operands for operator {}: expected comparable operands")


@pytest.mark.parametrize(
    ("name", "strict", "expected"),
    [
        ("set_earlier", False, _NOT_YET),
        ("set_earlier", True, ("PIE-S2336", _STRICT)),
        ("values_earlier", False, _VALUES_TYPE),
        ("table_function", False, (_CROSS[0], _CROSS[1].format(">="))),
        ("table_function", True, (_CROSS[0], _CROSS[1].format(">"))),
        ("target_let_block", False, _SOURCE_ONLY),
        ("target_let_block", True, ("PIE-S2336", _STRICT)),
        ("target_capture_let", False, _SOURCE_ONLY),
        ("target_capture_let", True, ("PIE-S2336", _STRICT)),
        ("in_let_body", False, _NOT_YET),
        ("in_let_body", True, ("PIE-S2336", _STRICT)),
        ("beside_a_let", False, _NOT_YET),
        ("beside_a_let", True, ("PIE-S2336", _STRICT)),
    ],
)
def test_a_project_lowers_an_asof_join_only_where_normalization_takes_its_any(
    tmp_path: Path, name: str, strict: bool, expected: tuple[str, str]
) -> None:
    """Elsewhere the JOIN stays as written: its own checks, then the refusal;
    no diagnostic of the internal any(...) reaches the author."""

    source = SHAPES.format(connector="postgres") + "\nquery q:\n" + _UNLOWERED[name]
    if strict:
        source = source.replace("ordered_at >= price", "ordered_at > price")
        source = source.replace("n.n >= rate", "n.n > rate")
    assert _project_diagnostics(tmp_path / "p", source) == [expected]
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None
    assert lower_latest_rows(parsed.ast) is parsed.ast


_PARENT = (
    "\nquery parent:\n    let all_prices:\n        from prices\n        select:\n"
    "            product_id\n            valid_from\n        order by product_id\n"
    "    from orders\n    select:\n        id\n        product_id\n"
    "        ordered_at\n        nested = collect all_prices\n"
)
_FLAT_ONLY = ("PIE-S2336", "Do the asof JOIN in a query with only flat fields first.")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "    from parent\n    let o = unnest(parent.nested)\n    cross join o\n"
            "    let price = prices\n    asof left join price on "
            + _ON.format(e="parent")
            + "\n    select i = o.product_id\n",
            _FLAT_ONLY,
        ),
        (
            "    from parent\n    let price = prices\n    asof left join price on "
            + _ON.format(e="parent")
            + "\n    select i = parent.id\n",
            _FLAT_ONLY,
        ),
        (
            "    from orders\n    let price = parent\n    asof left join price on "
            + _ON.format(e="orders").replace("price.valid_from", "price.ordered_at")
            + "\n    select i = orders.id\n",
            _SOURCE_ONLY,
        ),
    ],
    ids=["beside_unnest", "earlier_nested", "nested_query_target"],
)
def test_a_project_refuses_an_asof_join_over_nested_fields_before_lowering(
    tmp_path: Path, query: str, expected: tuple[str, str]
) -> None:
    """No latest-row `any(...)` is made beside an unnest, and a query target
    is no source whatever its fields."""

    source = SHAPES.format(connector="postgres") + _PARENT + "\nquery q:\n" + query
    assert _project_diagnostics(tmp_path / "p", source) == [expected]


@pytest.mark.parametrize("name", ["target_capture_let", "target_let_block"])
def test_an_unlowered_project_asof_join_keeps_its_kind_refusal(
    tmp_path: Path, name: str
) -> None:
    """A capture-let target gives the asof kind text, not its own JOIN-kind
    refusal, whose hint offers `cross join`."""

    source = SHAPES.format(connector="postgres") + "\nquery q:\n" + _UNLOWERED[name]
    source = source.replace("asof left join", "asof right join")
    assert _project_diagnostics(tmp_path / "p", source) == [
        ("PIE-S2336", ASOF_KIND_MESSAGE)
    ]


@pytest.mark.parametrize("name", ["beside_a_let", "in_let_body"])
def test_an_unlowered_project_asof_join_keeps_its_uniqueness_proof(
    tmp_path: Path, name: str
) -> None:
    source = SHAPES.format(connector="postgres") + "\nquery q:\n" + _UNLOWERED[name]
    source = source.replace("let price = prices\n", "let price = prices_none\n")
    message = _UNIQUE[_UNIQUE_IDS.index("no_unique")][1]
    assert _project_diagnostics(tmp_path / "p", source) == [("PIE-S2386", message)]


def test_a_project_refuses_an_aggregate_over_an_asof_join(tmp_path: Path) -> None:
    """v1: a project proves no single joined row, so it refuses an aggregate
    after an asof JOIN that a single file admits over the earlier input."""

    source = asof_query(
        f"asof left join price on {KEY} and {TIME}",
        after="    group by orders.product_id\n",
        select="select p = orders.product_id, n = sum(orders.amount)",
    )
    assert _diagnostics(source) == []
    assert _project_diagnostics(tmp_path / "p", source) == [
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: q (an aggregate "
            "may read rows repeated by JOIN price; use `any(...)` for an input that "
            "only filters rows, or aggregate in a separate query first)",
        )
    ]


def test_a_project_admits_an_aggregate_when_the_asof_keys_match_a_unique_key(
    tmp_path: Path,
) -> None:
    """The ordinary JOIN proof: the asof `on` key matches `unique(id)`."""

    source = asof_query(
        "asof left join price on orders.id == price.id and "
        "orders.ordered_at >= price.valid_from",
        let="let price = prices_id",
        after="    group by orders.product_id\n",
        select="select p = orders.product_id, n = sum(orders.amount)",
    )
    assert _diagnostics(source) == []
    assert _project_diagnostics(tmp_path / "p", source) == []


@pytest.mark.parametrize(
    ("lines", "relation"),
    [
        ("    let price = prices\n    asof left join price", "prices"),
        ("    let p = prices\n    let price = p\n    asof left join price", "prices"),
        ("    asof inner join prices", "prices"),
    ],
    ids=["let", "let_chain", "direct"],
)
def test_a_project_lowers_an_asof_join_to_its_latest_row_test(
    lines: str, relation: str
) -> None:
    target = lines.rsplit(" ", 1)[1]
    source = SHAPES.format(connector="postgres") + (
        f"\nquery q:\n    from orders\n{lines} on orders.product_id == "
        f"{target}.product_id and orders.ordered_at >= {target}.valid_from\n"
        "    select order_id = orders.id\n"
    )
    parsed = parse_source(source, path="asof.pietto")
    assert parsed.ast is not None
    lowered = lower_latest_rows(parsed.ast)
    (clause,) = _query(lowered).join_clauses
    assert clause.on_clause is not None
    on = clause.on_clause.expression
    assert type(on) is BinaryExpr and on.operator == "and"
    authored, latest = on.left, on.right
    (written,) = _query(parsed.ast).join_clauses
    assert written.on_clause is not None
    assert authored is written.on_clause.expression
    assert type(latest) is UnaryExpr and latest.operator == "not"
    found = latest.operand
    assert type(found) is AnyExpr
    assert (found.binding_name, found.relation_name) == (
        "_pietto_asof_later_1",
        relation,
    )
    later = found.binding_name
    assert _tests(found.predicate) == [
        ("orders.product_id", "==", f"{later}.product_id"),
        ("orders.ordered_at", ">=", f"{later}.valid_from"),
        (f"{later}.valid_from", ">", f"{target}.valid_from"),
    ]
    spans = [node.span for node in _nodes(latest)]
    assert all(span.occurrence for span in spans)
    assert len(set(spans)) == len(spans)
    # Semantics reads the authored form: the latest-row test is no conjunct of it.
    form = asof_form(clause, {"orders"}, "orders")
    assert type(form) is AsofForm
    assert [
        (".".join(a.parts), ".".join(b.parts)) for a, b in (*form.keys, form.time)
    ] == [
        ("orders.product_id", f"{target}.product_id"),
        ("orders.ordered_at", f"{target}.valid_from"),
    ]
    # A refused form is not lowered.
    strict = parse_source(source.replace(">=", ">"), path="asof.pietto")
    assert strict.ast is not None
    assert lower_latest_rows(strict.ast) is strict.ast


def _tests(node: object) -> list[tuple[str, str, str]]:
    if type(node) is BinaryExpr and node.operator == "and":
        return [*_tests(node.left), *_tests(node.right)]
    assert type(node) is ComparisonExpr
    assert type(node.left) is DottedNameExpr and type(node.right) is DottedNameExpr
    return [(".".join(node.left.parts), node.operator, ".".join(node.right.parts))]


def _query(script: Script) -> QueryDef:
    query = script.definitions[-1]
    assert type(query) is QueryDef
    return query


def _nodes(node: Any) -> list[Any]:
    found = [node]
    for name in ("operand", "predicate", "left", "right"):
        child = getattr(node, name, None)
        if child is not None:
            found.extend(_nodes(child))
    return found
