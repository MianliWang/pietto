"""The conditional count and sum of a group (Phase73 S02): a generator's
meaning is fixed by its source alone, only `sum` over `group` is admitted, and
every other generator use is one diagnostic with its hint."""

from __future__ import annotations

import pytest

from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

PREFIX = """type Cents = Int
shape Order:
    id: Int
    customer_id: Int | None
    amount: Cents
    price: Float
    paid: Bool
    status: Text | None
shape Customer:
    id: Int
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
def big(x: Int) -> Bool:
    return x > 10
"""
LINE = PREFIX.count("\n") + 4  # the select line of `_grouped`


def _grouped(call: str) -> str:
    return (
        "query q:\n    from orders\n    group by customer_id\n"
        f"    select customer_id, n = {call}\n"
    )


def _analyze(body: str) -> SemanticResult:
    parsed = parse_source(PREFIX + body)
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    return analyze(parsed.ast)


def _rows(
    result: SemanticResult,
) -> list[tuple[str, str, int, int | None, str, str | None]]:
    return [
        (
            item.code,
            item.severity.value,
            item.location.line,
            item.location.column,
            item.message,
            item.suggestion,
        )
        for item in result.diagnostics
    ]


def _at(text: str, call: str) -> int:
    """The column of ``text`` on the select line of `_grouped` of ``call``."""

    return ("    select customer_id, n = " + call).index(text) + 1


@pytest.mark.parametrize(
    "call",
    [
        "sum(1 for o in group if o.paid)",
        "sum(o.amount for o in group if o.paid and o.status == 'x')",
        "sum(1 for o in group if big(o.amount) and customer_id == 3)",
    ],
)
def test_a_group_generator_sum_is_a_non_none_int(call: str) -> None:
    result = _analyze(_grouped(call.replace("'", '"')))

    assert result.diagnostics == ()
    (relation,) = (
        schema
        for definition, schema in result.model.relation_row_schemas.items()
        if getattr(definition, "name", None) == "q"
    )
    field = relation.fields["n"]
    assert (field.resolved_type.name, field.nullability.value) == ("Int", "non_null")


def test_an_aggregate_query_without_group_by_reads_its_whole_input_as_a_group() -> None:
    result = _analyze(
        "query q:\n    from orders\n    select:\n"
        "        n = sum(1 for o in group if o.paid)\n"
        "        s = sum(o.amount for o in group if o.paid)\n"
    )

    assert result.diagnostics == ()


_ALL = "only `sum(... for o in group if ...)` takes a generator"
_BEFORE_GROUPS = (
    "a group's rows exist only after `group by`; test a row's own fields directly"
)
_COUNT = "count matching rows with `sum(1 for o in group if ...)`"


@pytest.mark.parametrize(
    ("call", "at", "code", "message", "hint"),
    [
        (
            "sum(1 for o in orders if o.paid)",
            "orders",
            "PIE-S2334",
            "Generator over orders in sum: orders is the whole relation, not "
            "this group",
            "for this group's rows write `for o in group`",
        ),
        (
            "sum(1 for o in grp if o.paid)",
            "grp",
            "PIE-S2301",
            "Unknown or unavailable generator source: grp",
            "for this group's rows write `for o in group`",
        ),
        (
            "sum(o.amount for o in orders.items if o.paid)",
            "orders.items",
            "PIE-S2334",
            "A generator over orders.items is not available yet",
            "`len`, `sum` and `any` over a row's collected list are a coming feature",
        ),
        (
            "count(1 for o in group if o.paid)",
            "count",
            "PIE-S2334",
            "count takes no generator",
            _COUNT,
        ),
        (
            "len(o for o in group if o.paid)",
            "len",
            "PIE-S2334",
            "len takes no generator",
            _COUNT,
        ),
        (
            "max(o.amount for o in group if o.paid)",
            "max",
            "PIE-S2334",
            "max takes no generator; a conditional max is not available",
            _ALL,
        ),
        (
            "lower(o.status for o in group if o.paid)",
            "lower",
            "PIE-S2334",
            "A generator is only the argument of sum or any",
            None,
        ),
        (
            "count_if(1 for o in group if o.paid)",
            "count_if",
            "PIE-S2103",
            "Unknown function: count_if",
            "write `sum(1 for o in group if ...)` or `sum(o.v for o in group if ...)`",
        ),
        (
            "sum(1 for o in group)",
            "sum",
            "PIE-S2334",
            "sum(1 for o in group) counts every row of the group",
            "write `count()`",
        ),
        (
            "sum(o.amount for o in group)",
            "sum",
            "PIE-S2334",
            "sum(o.amount for o in group) adds every row of the group",
            "write `sum(amount)`",
        ),
        (
            "sum(o.amount if o.paid else 0 for o in group if o.paid)",
            "sum",
            "PIE-S2315",
            "Aggregate function sum of a generator adds 1 or one field of o; "
            "expression bodies are not supported yet",
            "filter with `if` after the source: `sum(o.f for o in group if ...)`",
        ),
        (
            "sum(amount for o in group if o.paid)",
            "sum",
            "PIE-S2315",
            "Aggregate function sum of a generator adds 1 or one field of o; "
            "expression bodies are not supported yet",
            "read the member as `o.amount`",
        ),
        (
            "sum(2 for o in group if o.paid)",
            "sum",
            "PIE-S2315",
            "Aggregate function sum of a generator adds 1 or one field of o; "
            "expression bodies are not supported yet",
            None,
        ),
        (
            "sum(1 for o in group if paid)",
            "paid)",
            "PIE-S2334",
            "Generator reads paid outside its member",
            "write `o.paid`",
        ),
        (
            "sum(1 for o in group if orders.paid)",
            "orders.paid",
            "PIE-S2334",
            "Generator reads orders.paid outside its member",
            "write `o.paid`",
        ),
        (
            "sum(1 for o in group if o)",
            "o)",
            "PIE-S2334",
            "Generator reads its member o as a value",
            "read a field of it: `o.f`",
        ),
        (
            "sum(1 for o in group if o.a.b)",
            "o.a.b",
            "PIE-S2102",
            "Unknown or unavailable field in generator: o.a.b",
            None,
        ),
        (
            "sum(1 for o in group if count() > 1)",
            "count()",
            "PIE-S2311",
            "Nested aggregate count() is not supported",
            None,
        ),
        (
            "sum(1 for o in group if any(c.id == o.id for c in customers))",
            "any(",
            "PIE-S2334",
            "A generator test reads one member row: no window, any(...), "
            "generator, relation read or captured field",
            None,
        ),
        (
            "sum(1 for o in group if o.paid) + 1",
            "sum",
            "PIE-S2310",
            "Aggregate projection must be a direct aggregate call; composition "
            "around sum() is not supported yet",
            None,
        ),
    ],
)
def test_each_refused_generator_reports_its_first_broken_rule(
    call: str, at: str, code: str, message: str, hint: str | None
) -> None:
    result = _analyze(_grouped(call))

    text = message if hint is None else f"{message}; {hint}"
    assert _rows(result) == [(code, "error", LINE, _at(at, call), text, hint)]


@pytest.mark.parametrize(
    ("body", "line", "column", "code", "message", "hint"),
    [
        (
            "query q:\n    from customers\n"
            "    where any(o.paid for o in orders if o.customer_id == customers.id)\n"
            "    select id\n",
            3,
            11,
            "PIE-S2334",
            "any takes its test in the body",
            "write `any(p and q for o in r)`",
        ),
        (
            "query q:\n    from customers\n"
            "    where any(True for o in orders if o.customer_id == customers.id)\n"
            "    select id\n",
            3,
            11,
            "PIE-S2334",
            "any takes its test in the body",
            "write `any(q for o in r)`",
        ),
        (
            "query q:\n    from customers\n"
            "    select id, n = sum(1 for o in orders if o.customer_id == customers.id)\n",
            3,
            35,
            "PIE-S2334",
            "Generator over orders in sum: orders is the whole relation, not "
            "this group",
            "count per key in a grouped query and join it on the key",
        ),
        (
            "query q:\n    from orders\n    where sum(1 for o in group if o.paid) > 0\n"
            "    group by customer_id\n    select customer_id, n = count()\n",
            3,
            11,
            "PIE-S2308",
            "Aggregate sum() is not allowed in where clause; use it only as a "
            "direct aliased select projection",
            _BEFORE_GROUPS,
        ),
        (
            "query q:\n    from orders\n    let n = sum(1 for o in group if o.paid)\n"
            "    group by customer_id\n    select customer_id, c = count()\n",
            3,
            13,
            "PIE-S2308",
            "Aggregate sum() is not allowed in let binding; use it only as a "
            "direct aliased select projection",
            _BEFORE_GROUPS,
        ),
        (
            "query q:\n    from orders\n    group by customer_id\n"
            "    select customer_id, n = count()\n"
            "    having sum(1 for o in group if o.paid) > 0\n",
            5,
            12,
            "PIE-S2308",
            "Aggregate sum() is not allowed in having clause; use it only as a "
            "direct aliased select projection",
            None,
        ),
        (
            "query q:\n    from orders\n    group by customer_id\n"
            "    select customer_id, sum(1 for o in group if o.paid)\n",
            4,
            25,
            "PIE-S2313",
            "Aggregate sum() projection requires an explicit alias",
            None,
        ),
        (
            "query q:\n    from orders\n"
            "    inner join customers on orders.customer_id == customers.id\n"
            "    group by orders.customer_id\n"
            "    select customer_id, n = sum(1 for o in group if o.paid)\n",
            5,
            29,
            "PIE-S2334",
            "sum(... for o in group ...) over JOIN rows is not available yet",
            "join in one query, then group it in another that reads it with `from`",
        ),
        (
            "def counted() -> Int:\n    return sum(1 for o in group if o.paid)\n",
            2,
            12,
            "PIE-S2308",
            "Aggregate sum() is not allowed in this position; use it only as a "
            "direct aliased select projection",
            _BEFORE_GROUPS,
        ),
    ],
)
def test_generators_outside_a_group_select_item_are_refused(
    body: str, line: int, column: int, code: str, message: str, hint: str | None
) -> None:
    result = _analyze(body)

    text = message if hint is None else f"{message}; {hint}"
    first = PREFIX.count("\n")
    assert _rows(result) == [(code, "error", first + line, column, text, hint)]


@pytest.mark.parametrize(
    ("call", "message", "hint"),
    [
        (
            "sum(o.paid for o in group if o.paid)",
            "Aggregate function sum of a generator adds an Int field of o, got Bool",
            "count with `sum(1 for o in group if o.paid)`",
        ),
        (
            "sum(o.status for o in group if o.paid)",
            "Aggregate function sum of a generator adds an Int field of o, got Text",
            None,
        ),
        (
            "sum(o.price for o in group if o.paid)",
            "Aggregate function sum of a generator adds an Int field of o; a "
            "Float or Decimal sum is not available yet",
            None,
        ),
    ],
)
def test_a_generator_sum_adds_int_fields_only(
    call: str, message: str, hint: str | None
) -> None:
    result = _analyze(_grouped(call))

    text = message if hint is None else f"{message}; {hint}"
    assert _rows(result) == [("PIE-S2314", "error", LINE, 29, text, hint)]


def test_member_reads_and_the_test_are_typed_as_input_row_reads() -> None:
    result = _analyze(
        _grouped("sum(o.nosuch for o in group if o.paid)")
        + "query r:\n    from orders\n    group by customer_id\n"
        "    select customer_id, n = sum(1 for o in group if o.amount)\n"
    )

    assert _rows(result) == [
        ("PIE-S2102", "error", LINE, 33, "Unknown field: nosuch", None),
        (
            "PIE-S2202",
            "error",
            LINE + 4,
            53,
            "Expected Bool expression in generator test",
            None,
        ),
    ]


def test_a_generator_needs_the_field_types_of_its_input() -> None:
    parsed = parse_source(
        'source raw = postgres.table("raw")\n'
        "query q:\n    from raw\n    group by k\n"
        "    select k, n = sum(1 for o in group if o.paid)\n"
    )
    assert parsed.ast is not None
    errors = [
        item
        for item in analyze(parsed.ast).diagnostics
        if item.severity is Severity.ERROR
    ]

    assert [(item.code, item.location.line, item.message) for item in errors] == [
        (
            "PIE-S2334",
            5,
            "sum(... for o in group ...) reads an input whose fields are not "
            "known; give its source a shape",
        )
    ]


def test_a_relation_named_group_keeps_its_meaning_and_is_refused_in_sum() -> None:
    """`from group` and `any(... for o in group)` read the relation, as
    before; `sum` over it is the whole relation, refused with a rename hint."""
    source = (
        PREFIX.replace(
            "source customers:",
            'source group: Order = postgres.table("shop.g")\nsource customers:',
        )
        + "query reads:\n    from group\n    select id\n"
        + "query tests:\n    from customers\n"
        "    where any(o.customer_id == customers.id for o in group)\n"
        "    select id\n" + _grouped("sum(1 for o in group if o.paid)")
    )
    parsed = parse_source(source)
    assert parsed.ast is not None
    rows = _rows(analyze(parsed.ast))

    hint = "rename the relation group to read this group's rows"
    assert rows == [
        (
            "PIE-S2334",
            "error",
            source.count("\n"),
            44,
            "Generator over group in sum: group is the relation group, not this "
            f"group; {hint}",
            hint,
        )
    ]


def test_a_let_named_group_keeps_its_meaning_and_is_refused_in_sum() -> None:
    accepted = _analyze(
        "query q:\n    let group = orders\n    from customers\n"
        "    where any(o.customer_id == customers.id for o in group)\n"
        "    select id\n"
    )
    refused = _analyze(
        "query q:\n    let group = customers\n    from orders\n"
        "    group by customer_id\n"
        "    select customer_id, n = sum(1 for o in group if o.paid)\n"
    )

    hint = "rename the let group to read this group's rows"
    assert accepted.diagnostics == ()
    assert _rows(refused) == [
        (
            "PIE-S2334",
            "error",
            PREFIX.count("\n") + 5,
            44,
            "Generator over group in sum: group is the let group, not this group; "
            + hint,
            hint,
        )
    ]


_GROUP_TEST = (
    "a group test is not available yet: select "
    "`n = sum(1 for o in group if ...)` and test `n > 0` in `having` or a later query"
)


def test_any_over_group_keeps_its_error_and_names_the_conditional_count() -> None:
    result = _analyze(_grouped("any(o.paid for o in group)"))
    having = (
        "query q:\n    from orders\n    group by customer_id\n"
        "    select customer_id, c = count()\n    having any(o.paid for o in {})\n"
    )

    assert [
        (item.code, item.message, item.suggestion)
        for name in ("group", "orders")
        for item in _analyze(having.format(name)).diagnostics
    ] == [
        ("PIE-S2334", "ANY is not supported in this context", _GROUP_TEST),
        ("PIE-S2334", "ANY is not supported in this context", None),
    ]
    assert _rows(result) == [
        (
            "PIE-S2319",
            "error",
            LINE,
            29,
            "Grouped scalar projection expressions are not supported yet",
            None,
        ),
        (
            "PIE-S2301",
            "error",
            LINE,
            49,
            "Unknown or unavailable ANY relation: group",
            _GROUP_TEST,
        ),
    ]


def test_conditional_habits_without_a_generator_name_it() -> None:
    result = _analyze(
        "query q:\n    from orders\n    group by customer_id\n    select:\n"
        "        customer_id\n"
        "        a = sum(amount if paid else 0)\n"
        "        b = count(1 if paid else None)\n"
        "        c = sum(paid)\n"
        "        d = SumIf(amount)\n"
    )

    first = PREFIX.count("\n") + 6
    hints = [
        "write `sum(o.v for o in group if ...)`",
        "write `sum(1 for o in group if ...)`",
        "count with `sum(1 for o in group if o.paid)`",
        "write `sum(1 for o in group if ...)` or `sum(o.v for o in group if ...)`",
    ]
    assert [
        (code, line - first, column, message, hint)
        for code, _, line, column, message, hint in _rows(result)
    ] == [
        (
            "PIE-S2315",
            0,
            13,
            "Aggregate function sum requires a direct field argument; expression "
            f"arguments are not supported yet; {hints[0]}",
            hints[0],
        ),
        (
            "PIE-S2315",
            1,
            13,
            "Aggregate function count requires a direct field argument; "
            f"expression arguments are not supported yet; {hints[1]}",
            hints[1],
        ),
        (
            "PIE-S2314",
            2,
            13,
            "Aggregate function sum expects Int, Float, or Decimal field argument, "
            f"got Bool; {hints[2]}",
            hints[2],
        ),
        ("PIE-S2103", 3, 13, f"Unknown function: SumIf; {hints[3]}", hints[3]),
        (
            "PIE-S2319",
            3,
            13,
            "Grouped scalar projection expressions are not supported yet",
            None,
        ),
    ]


def test_count_of_a_bool_field_warns_that_false_counts_too() -> None:
    result = _analyze(
        "query q:\n    from orders\n    group by customer_id\n    select:\n"
        "        customer_id\n"
        "        seen = count(paid)\n"
        "        seen_too = count(orders.paid)\n"
        "        amounts = count(amount)\n"
    )
    # In a window no generator is written, so no conditional count is named.
    windowed = _analyze(
        "query q:\n    from orders\n    select:\n        id\n"
        "        c = count(paid) window(partition by customer_id)\n"
    )

    assert windowed.diagnostics == ()

    first = PREFIX.count("\n") + 6
    assert [
        (item.code, item.severity, item.location.line - first, item.message)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2388",
            Severity.WARNING,
            line,
            f"`count({written})` counts every row whose paid is not None, False "
            "included; to count the rows where it is True, write "
            "`sum(1 for o in group if o.paid)`",
        )
        for line, written in ((0, "paid"), (1, "orders.paid"))
    ]
