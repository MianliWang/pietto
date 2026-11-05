"""The backward asof JOIN: admitted forms and every refused variant.

An `asof left join` or `asof inner join` keeps, for each earlier row, the
latest joined row whose keys match and whose time is at or before the
earlier row's; a declared unique within the keys and the time proves at
most one. Each refused variant is one diagnostic with its hint.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _pietto_semantic_join_asof import CANONICAL, JOIN_LINE, KEY, TIME, asof_query
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.errors import Severity
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
    "asof_right": ("asof right join price on {KEY} and {TIME}", "S2336", _KIND),
    "asof_full": ("asof full join price on {KEY} and {TIME}", "S2336", _KIND),
    "asof_cross": ("asof cross join price", "S2336", _KIND),
    "asof_semi": ("asof semi join price on {KEY} and {TIME}", "S2336", _KIND),
    "asof_anti": ("asof anti join price on {KEY} and {TIME}", "S2336", _KIND),
    "missing_on": (
        "asof left join price",
        "S2335",
        "JOIN price: write `on` with the keys, then one time test: "
        "`on orders.k == price.k and orders.t >= price.t`",
    ),
    "no_time": (
        "asof left join price on {KEY}",
        "S2336",
        "Add one time test last: `and orders.t >= price.t`.",
    ),
    "strict": (
        "asof left join price on {KEY} and orders.ordered_at > price.valid_from",
        "S2336",
        _STRICT,
    ),
    "strict_reversed": (
        "asof left join price on {KEY} and price.valid_from < orders.ordered_at",
        "S2336",
        _STRICT,
    ),
    "reversed_time": (
        "asof left join price on {KEY} and price.valid_from <= orders.ordered_at",
        "S2336",
        "Write the earlier input first in each test: "
        "`orders.ordered_at >= price.valid_from`.",
    ),
    "reversed_key": (
        "asof left join price on price.product_id == orders.product_id and {TIME}",
        "S2336",
        "Write the earlier input first in each test: "
        "`orders.product_id == price.product_id`.",
    ),
    "forward_le": (
        "asof left join price on {KEY} and orders.ordered_at <= price.valid_from",
        "S2336",
        _FORWARD,
    ),
    "forward_lt": (
        "asof left join price on {KEY} and orders.ordered_at < price.valid_from",
        "S2336",
        _FORWARD,
    ),
    "forward_reversed_ge": (
        "asof left join price on {KEY} and price.valid_from >= orders.ordered_at",
        "S2336",
        _FORWARD,
    ),
    "forward_reversed_gt": (
        "asof left join price on {KEY} and price.valid_from > orders.ordered_at",
        "S2336",
        _FORWARD,
    ),
    "time_first": (
        "asof left join price on {TIME} and {KEY}",
        "S2336",
        "Write the keys first and the one time test last.",
    ),
    "key_twice": (
        "asof left join price on {KEY} and {KEY} and {TIME}",
        "S2336",
        "Match each key once: remove the repeated "
        "`orders.product_id == price.product_id`.",
    ),
    "second_time_inner": (
        "asof inner join price on {KEY} and {TIME} and "
        "price.valid_from >= orders.week_start",
        "S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where price.valid_from >= orders.week_start`.",
    ),
    "second_time_left": (
        "asof left join price on {KEY} and {TIME} and "
        "price.valid_from >= orders.week_start",
        "S2336",
        _LEFT_EXTRA.format(test="price.valid_from >= orders.week_start"),
    ),
    "chain": (
        "asof left join price on {KEY} and "
        "orders.ordered_at >= price.valid_from >= orders.week_start",
        "S2336",
        _LEFT_EXTRA.format(test="price.valid_from >= orders.week_start"),
    ),
    "lower_before_inner": (
        "asof inner join price on {KEY} and orders.week_start <= price.valid_from "
        "and {TIME}",
        "S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where orders.week_start <= price.valid_from`.",
    ),
    "lower_before_left": (
        "asof left join price on {KEY} and orders.week_start <= price.valid_from "
        "and {TIME}",
        "S2336",
        _LEFT_EXTRA.format(test="orders.week_start <= price.valid_from"),
    ),
    "chain_le_left": (
        "asof left join price on {KEY} and "
        "orders.week_start <= price.valid_from <= orders.ordered_at",
        "S2336",
        _LEFT_EXTRA.format(test="orders.week_start <= price.valid_from").replace(
            "test; ", "test; keep `orders.ordered_at >= price.valid_from` in `on`; "
        ),
    ),
    "chain_le_inner": (
        "asof inner join price on {KEY} and "
        "orders.week_start <= price.valid_from <= orders.ordered_at",
        "S2336",
        "An asof `on` takes one time test; keep `orders.ordered_at >= "
        "price.valid_from` in `on`; test the chosen row after the JOIN instead: "
        "`where orders.week_start <= price.valid_from`.",
    ),
    "chain_lt_le_left": (
        "asof left join price on {KEY} and "
        "orders.week_start < price.valid_from <= orders.ordered_at",
        "S2336",
        _LEFT_EXTRA.format(test="orders.week_start < price.valid_from").replace(
            "test; ", "test; keep `orders.ordered_at >= price.valid_from` in `on`; "
        ),
    ),
    "chain_lt_le_inner": (
        "asof inner join price on {KEY} and "
        "orders.week_start < price.valid_from <= orders.ordered_at",
        "S2336",
        "An asof `on` takes one time test; keep `orders.ordered_at >= "
        "price.valid_from` in `on`; test the chosen row after the JOIN instead: "
        "`where orders.week_start < price.valid_from`.",
    ),
    "arithmetic": (
        "asof inner join price on {KEY} and orders.amount >= price.amount_cents + 1",
        "S2336",
        "An asof `on` takes one time test; test the chosen row after the JOIN "
        "instead: `where orders.amount >= price.amount_cents + 1`.",
    ),
    "validity_range": (
        "asof left join price on {KEY} and {TIME} and "
        "orders.ordered_at < price.valid_to",
        "S2336",
        "For a validity range, use `left join price on` with both tests.",
    ),
    "or": ("asof left join price on {KEY} or {TIME}", "S2336", _OTHER),
    "not_equal": (
        "asof left join price on orders.region != price.region and {TIME}",
        "S2336",
        _OTHER,
    ),
    "literal": (
        "asof left join price on price.amount_cents == 3 and {TIME}",
        "S2336",
        _OTHER,
    ),
    "same_input": (
        "asof left join price on orders.product_id == orders.amount and {TIME}",
        "S2336",
        _OTHER,
    ),
    "call": (
        "asof left join price on abs(orders.product_id) == price.product_id and {TIME}",
        "S2336",
        _OTHER,
    ),
    "relationship_call": (
        "asof left join price on order_price(orders, price) and {TIME}",
        "S2336",
        _OTHER,
    ),
    "in_list": (
        'asof left join price on {KEY} and price.region in ("a", "b") and {TIME}',
        "S2336",
        _OTHER,
    ),
    "is_none": (
        "asof left join price on price.region is None and {TIME}",
        "S2336",
        _OTHER,
    ),
    "bare": (
        "asof left join price on {KEY} and ordered_at >= price.valid_from",
        "S2336",
        "Qualify each field with its input.",
    ),
    "date_and_timestamp": (
        "asof left join price on {KEY} and orders.ordered_on >= price.valid_from",
        "S2336",
        _TYPES.format("Date", "Timestamp"),
    ),
    "int_time": (
        "asof left join price on {KEY} and orders.amount >= price.amount_cents",
        "S2336",
        _TYPES.format("Int", "Int"),
    ),
    "text_time": (
        "asof left join price on {KEY} and orders.region >= price.region",
        "S2336",
        _TYPES.format("Text", "Text"),
    ),
    "float_key": (
        "asof left join price on orders.score == price.score and {TIME}",
        "S2336",
        "An asof key cannot be Float.",
    ),
    # Precedence: a conjunct with its own error gets no form message.
    "cross_family": (
        "asof left join price on {KEY} and orders.region >= price.valid_from",
        "S2105",
        "Invalid operands for operator >=: expected comparable operands",
    ),
    "unknown_earlier": (
        "asof left join price on orders.nope == price.product_id and {TIME}",
        "S2335",
        "JOIN ON reference is unknown: orders.nope",
    ),
    "unknown_joined": (
        "asof left join price on {KEY} and orders.ordered_at >= price.nope",
        "S2335",
        "JOIN ON reference is unknown: price.nope",
    ),
    "kind_before_form": (
        "asof right join price on {KEY} and orders.ordered_at > price.valid_from",
        "S2336",
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
    assert [(code, message)] == [(item[1][4:], item[2]) for item in found]
    assert found[0][0] == JOIN_LINE


@pytest.mark.parametrize(
    ("let", "message"),
    [
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
    ],
    ids=[
        "table",
        "no_unique",
        "unique_id",
        "surrogate_first",
        "unique_outside_on",
        "unique_unmatched",
    ],
)
def test_one_latest_row_needs_a_source_unique_within_keys_and_time(
    let: str, message: str
) -> None:
    source = asof_query(
        f"asof left join price on {KEY} and {TIME}", let=let, select=_ONLY_ORDERS
    )
    assert _diagnostics(source) == [(JOIN_LINE, "PIE-S2386", message)]


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


def _project_diagnostics(root: Path, source: str) -> list[tuple[str, str]]:
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")
    project = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    return [(item.code, item.message) for item in project.diagnostics]


def test_a_project_refuses_every_asof_join_before_its_sql_plan(tmp_path: Path) -> None:
    assert _project_diagnostics(tmp_path / "p", CANONICAL) == [
        ("PIE-S2336", "asof JOIN is not available in projects yet.")
    ]
