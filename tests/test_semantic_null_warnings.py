"""PIE-S2383 and PIE-S2384: single-file warnings at tests that SQL's None
handling turns against a Python reading, and the null-tolerant or never-None
tests that stay silent."""

from __future__ import annotations

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode

_SHAPES = """shape Order:
    id: Int
    customer_id: Int
    status: Text
    note: Text | None
    amount: Int
    order_key = unique(id)

shape Customer:
    id: Int
    status: Text | None
    region_id: Int | None
    credit: Int | None
    customer_key = unique(id)

shape Region:
    id: Int
    name: Text
    owner_id: Int
    region_key = unique(id)

source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")

relationship CustomerRegion(customer: Customer, region: Region):
    customer.region_id == region.id

def is_open(s: Text | None) -> Bool | None:
    return s not in ("closed", "banned")
"""


def _left_join(binding: str) -> str:
    return (
        f"`{binding}` is None where `left join {binding.split('.')[0]}` finds no "
        "match, so this WHERE test is never True on those rows and drops them, as "
        f"`inner join {binding.split('.')[0]}` would; to keep them, move the test "
        "into the JOIN's `on`, or write "
        f"`inner join {binding.split('.')[0]}` if only matched rows are wanted"
    )


def _not_in(*names: str) -> str:
    which = " or ".join(f"`{name}`" for name in names)
    keep = " or ".join(f"{name} is None" for name in names)
    drop = " and ".join(f"{name} is not None" for name in names)
    return (
        f"`not in` is never True when {which} is None: SQL compares None as "
        "unknown, unlike Python, where `None not in (...)` is True; write "
        f"`... or {keep}` to accept None, or `{drop} and ...` to reject it"
    )


def _query(name: str, body: str) -> str:
    return f"query {name}:\n{body}"


_LEFT_O = (
    "    from customers\n"
    "    let o = orders\n"
    "    left join o on o.customer_id == customers.id\n"
)


def _located(source: str, diagnostics: tuple[Diagnostic, ...]) -> list[tuple]:
    """Each diagnostic as its code, the source text it spans and its message."""

    lines = source.splitlines()
    found = []
    for item in diagnostics:
        location = item.location
        assert location.end_line == location.line
        assert location.end_column is not None
        text = lines[location.line - 1][location.column - 1 : location.end_column - 1]
        found.append((item.code, item.severity, text, item.message))
    return found


def _check(body: str, mode: CheckMode | None = None) -> list[tuple]:
    source = _SHAPES + body
    parsed = parse_source(source, path="input.pietto")
    assert parsed.ast is not None, parsed.diagnostics
    return _located(source, analyze(parsed.ast, mode_override=mode).diagnostics)


@pytest.mark.parametrize("mode", [None, *CheckMode])
def test_a_where_test_on_the_null_extended_side_warns_in_every_check_mode(
    mode: CheckMode | None,
) -> None:
    body = _query(
        "paid",
        _LEFT_O
        + '    where o.status == "paid"\n    select customer_id = customers.id\n',
    )

    assert _check(body, mode) == [
        ("PIE-S2383", Severity.WARNING, 'o.status == "paid"', _left_join("o.status"))
    ]


def test_each_left_join_target_is_reported_once_at_its_first_rejecting_test() -> None:
    body = _query(
        "tests",
        "    from customers\n"
        "    let r = regions\n"
        "    left join r on CustomerRegion(customers, r)\n"
        "    let o = orders\n"
        "    left join o on o.customer_id == customers.id\n"
        "    where customers.id > 3 and r.name == o.status and -o.amount * 2 > 1 "
        "and 1 <= r.id <= 9 and 1 < o.amount < 9 and o.id in (1, 2)\n"
        "    select customer_id = customers.id\n",
    )

    assert _check(body) == [
        ("PIE-S2383", Severity.WARNING, "r.name == o.status", _left_join("r.name")),
        ("PIE-S2383", Severity.WARNING, "r.name == o.status", _left_join("o.status")),
    ]


@pytest.mark.parametrize(
    "where",
    [
        "o.id is None",
        'o.status == "paid" or o.id is None',
        'coalesce(o.status, "none") != "cancelled"',
        "customers.id > 3",
        "not any(x.customer_id == o.customer_id for x in orders)",
        "is_open(o.note) or o.note is None",
    ],
)
def test_a_null_tolerant_or_preserved_side_where_test_is_silent(where: str) -> None:
    body = _query(
        "kept", _LEFT_O + f"    where {where}\n    select customer_id = customers.id\n"
    )

    assert _check(body) == []


def test_tests_outside_where_and_after_inner_joins_are_silent() -> None:
    body = (
        _query(
            "inner_target",
            "    from customers\n"
            "    let o = orders\n"
            "    inner join o on o.customer_id == customers.id\n"
            '    where o.status == "paid"\n'
            "    select customer_id = customers.id\n",
        )
        + _query(
            "test_in_on",
            "    from customers\n"
            "    let o = orders\n"
            '    left join o on o.customer_id == customers.id and o.status == "paid"\n'
            "    select customer_id = customers.id\n",
        )
        + _query(
            "later_inner_match",
            "    from customers\n"
            "    let r = regions\n"
            "    left join r on CustomerRegion(customers, r)\n"
            "    let o = orders\n"
            "    inner join o on o.customer_id == r.owner_id\n"
            '    where r.name == "north"\n'
            "    select customer_id = customers.id\n",
        )
    )

    assert _check(body) == []


def test_not_in_over_a_value_declared_none_able_warns_in_each_clause() -> None:
    body = (
        _query(
            "where_field",
            '    from customers\n    where status not in ("closed", "banned")\n'
            "    select id\n",
        )
        + _query(
            "select_let_and_arithmetic",
            "    from customers\n"
            "    let s = status\n"
            "    where region_id + 1 not in (3, 4)\n"
            "    select:\n"
            "        id\n"
            '        open = s not in ("closed",)\n'
            "        low = region_id - credit not in (1,)\n",
        )
        + _query(
            "inside_any",
            "    from customers\n"
            "    where any(o.customer_id == customers.id and "
            'o.note not in ("x",) for o in orders)\n'
            "    select id\n",
        )
        + _query(
            "in_on",
            "    from customers\n"
            "    let o = orders\n"
            '    left join o on o.customer_id == customers.id and o.note not in ("x",)\n'
            "    select customer_id = customers.id\n",
        )
        + _query(
            "def_call",
            "    from customers\n    where is_open(status)\n    select id\n",
        )
    )

    assert _check(body) == [
        (
            "PIE-S2384",
            Severity.WARNING,
            'status not in ("closed", "banned")',
            _not_in("status"),
        ),
        (
            "PIE-S2384",
            Severity.WARNING,
            "region_id + 1 not in (3, 4)",
            _not_in("region_id"),
        ),
        ("PIE-S2384", Severity.WARNING, 's not in ("closed",)', _not_in("s")),
        (
            "PIE-S2384",
            Severity.WARNING,
            "region_id - credit not in (1,)",
            _not_in("region_id", "credit"),
        ),
        ("PIE-S2384", Severity.WARNING, 'o.note not in ("x",)', _not_in("o.note")),
        ("PIE-S2384", Severity.WARNING, 'o.note not in ("x",)', _not_in("o.note")),
        ("PIE-S2384", Severity.WARNING, "is_open(status)", _not_in("status")),
    ]


def test_a_not_in_where_test_on_the_null_extended_side_gets_both_warnings() -> None:
    body = _query(
        "both",
        _LEFT_O
        + '    where o.note not in ("x",)\n    select customer_id = customers.id\n',
    )

    assert _check(body) == [
        ("PIE-S2383", Severity.WARNING, 'o.note not in ("x",)', _left_join("o.note")),
        ("PIE-S2384", Severity.WARNING, 'o.note not in ("x",)', _not_in("o.note")),
    ]


@pytest.mark.parametrize(
    ("where", "expected"),
    [
        ('status not in ("closed",) or status is None', []),
        ('status is not None and status not in ("closed",)', []),
        ('customers.status not in ("closed",) or status is None', []),
        ('coalesce(status, "") not in ("closed",)', []),
        ('lower(status) not in ("closed",)', []),
        ('status in ("open",)', []),
        ("id not in (1, 2)", []),
        (
            'status not in ("closed", None)',
            [
                (
                    "PIE-S2107",
                    Severity.WARNING,
                    'status not in ("closed", None)',
                    "A `None` option makes `not in` never true: SQL tests "
                    "`x != None`, which is never true; write "
                    '`x != "a" and x is not None`',
                )
            ],
        ),
    ],
)
def test_a_not_in_that_says_what_none_does_or_cannot_meet_none_has_no_nullable_warning(
    where: str, expected: list[tuple]
) -> None:
    body = _query("kept", f"    from customers\n    where {where}\n    select id\n")

    assert _check(body) == expected


def test_a_where_is_not_none_conjunct_silences_not_in_in_every_clause() -> None:
    body = (
        _query(
            "select_item",
            "    from customers\n"
            "    where status is not None\n"
            '    select open = status not in ("closed",)\n',
        )
        + _query(
            "order_key",
            "    from customers\n"
            "    where region_id is not None and id > 1\n"
            "    select id\n"
            "    order by region_id not in (1,)\n",
        )
        + _query(
            "join_select",
            "    from customers\n"
            "    let o = orders\n"
            "    inner join o on o.customer_id == customers.id\n"
            "    where customers.region_id is not None\n"
            "    select flag = customers.region_id not in (1,)\n",
        )
        + _query(
            "let_guard",
            "    from customers\n"
            "    let ok = status is not None\n"
            '    where ok and status not in ("closed",)\n'
            "    select id\n",
        )
        + _query(
            "let_alias",
            "    from customers\n"
            "    let s = status\n"
            '    where s is not None and s not in ("closed",)\n'
            '    select open = status not in ("closed",)\n',
        )
    )

    assert _check(body) == []


@pytest.mark.parametrize(
    "where",
    ["status is not None or id > 1", "status is None", "region_id is not None"],
)
def test_a_where_that_keeps_none_rows_does_not_silence_not_in_elsewhere(
    where: str,
) -> None:
    body = _query(
        "kept",
        f'    from customers\n    where {where}\n    select open = status not in ("closed",)\n',
    )

    assert _check(body) == [
        ("PIE-S2384", Severity.WARNING, 'status not in ("closed",)', _not_in("status"))
    ]


def test_a_test_that_already_has_an_error_gets_no_null_warning() -> None:
    body = _query(
        "broken",
        _LEFT_O + "    where o.note == None\n    select customer_id = customers.id\n",
    )

    assert [item[:3] for item in _check(body)] == [
        ("PIE-S2105", Severity.ERROR, "o.note == None")
    ]


def test_not_in_over_a_field_only_a_join_fills_with_none_is_silent() -> None:
    body = _query(
        "matched_status",
        _LEFT_O
        + "    select:\n"
        + "        customer_id = customers.id\n"
        + '        open = o.status not in ("closed",)\n',
    )

    assert _check(body) == []


def test_not_in_over_a_field_of_unknown_nullability_is_silent() -> None:
    source = (
        'source raw = postgres.table("raw")\n'
        "query q:\n"
        "    from raw\n"
        '    where status not in ("closed",)\n'
        "    select id\n"
    )
    parsed = parse_source(source, path="input.pietto")
    assert parsed.ast is not None

    codes = {item.code for item in analyze(parsed.ast).diagnostics}

    assert not codes & {"PIE-S2383", "PIE-S2384"}
