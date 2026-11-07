"""The conditional count and sum of a group (Phase73 S02) and the test of a
group: a generator's meaning is fixed by its source alone, only `sum`, `any`
and `all` over `group` are admitted, and every other generator use is one
diagnostic with its hint."""

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


_ALL = (
    "only `sum(... for o in group if ...)`, `any(...)` and `all(...)` take a generator"
)
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
            "A generator over orders.items reads a row's collected list, which "
            "only a project collects",
            "`sum` and `any` read a collected list in a project whose "
            "pietto.toml sets `schema_version = 2`",
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
            "A generator is only the argument of sum, any or all",
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
            "write `any(p and q for o in orders)`",
        ),
        (
            "query q:\n    from customers\n"
            "    where any(True for o in orders if o.customer_id == customers.id)\n"
            "    select id\n",
            3,
            11,
            "PIE-S2334",
            "any takes its test in the body",
            "write `any(q for o in orders)`",
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


def _schema_field(result: SemanticResult, relation: str, name: str) -> tuple[str, str]:
    (schema,) = (
        schema
        for definition, schema in result.model.relation_row_schemas.items()
        if getattr(definition, "name", None) == relation
    )
    field = schema.fields[name]
    return field.resolved_type.name, field.nullability.value


@pytest.mark.parametrize(
    "body",
    [
        _grouped("any(o.paid for o in group)"),
        _grouped("all(o.paid and o.status == 'x' for o in group)".replace("'", '"')),
        _grouped("all(not o.paid or customer_id > 3 for o in group)"),
        "query q:\n    from orders\n    select:\n"
        "        n = all(big(o.amount) for o in group)\n"
        "        s = sum(1 for o in group if o.paid)\n",
        "query q:\n    from orders\n    group by customer_id\n    select:\n"
        "        customer_id\n        n = any(o.status is None for o in group)\n"
        "    having n\n    order by n desc\n",
    ],
    ids=("any", "all", "key", "no_group_by", "having"),
)
def test_a_group_test_is_a_bool_that_is_never_none(body: str) -> None:
    """`any(TEST for o in group)` and `all(TEST for o in group)` are a whole
    aliased SELECT item; `having` and `order by` read the output."""
    result = _analyze(body)

    assert result.diagnostics == ()
    assert _schema_field(result, "q", "n") == ("Bool", "non_null")


_BEFORE = "a group's rows exist only after `group by`; test a row's own fields directly"
_RENAME = "rename the relation group to read this group's rows"


@pytest.mark.parametrize(
    ("call", "at", "code", "message", "hint"),
    [
        (
            "all(o.paid for o in group if o.amount > 1)",
            "all",
            "PIE-S2334",
            "all takes its test in the body",
            "count the exceptions: `n = sum(1 for o in group if q and not p)`, "
            "then `having n == 0`",
        ),
        (
            "all(o.paid for o in orders)",
            "orders",
            "PIE-S2334",
            "Generator over orders in all: orders is the whole relation, not this "
            "group",
            "for this group's rows write `for o in group`; all over a whole "
            "relation is not available",
        ),
        (
            "any(o.paid for o in group if o.amount > 1)",
            "any",
            "PIE-S2334",
            "any takes its test in the body",
            "write `any(p and q for o in group)`",
        ),
        (
            "all(paid for o in group)",
            "paid for",
            "PIE-S2334",
            "Generator reads paid outside its member",
            "write `o.paid`",
        ),
        (
            "any(o.paid and any(c.id == o.id for c in customers) for o in group)",
            "any(c",
            "PIE-S2334",
            "A generator test reads one member row: no window, any(...), "
            "generator, relation read or captured field",
            None,
        ),
        (
            "all(count() > 1 for o in group)",
            "count()",
            "PIE-S2311",
            "Nested aggregate count() is not supported",
            None,
        ),
        (
            "not all(o.paid for o in group)",
            "not",
            "PIE-S2310",
            "Aggregate projection must be a direct aggregate call; composition "
            "around all() is not supported yet",
            None,
        ),
        (
            "any(o.paid for o in group) and True",
            "any",
            "PIE-S2310",
            "Aggregate projection must be a direct aggregate call; composition "
            "around any() is not supported yet",
            None,
        ),
        (
            "max(paid)",
            "max",
            "PIE-S2314",
            "Aggregate function max expects Int, Float, Decimal, Date, or "
            "Timestamp field argument, got Bool",
            "for a test of the group write `any(o.paid for o in group)`",
        ),
        (
            "min(paid)",
            "min",
            "PIE-S2314",
            "Aggregate function min expects Int, Float, Decimal, Date, or "
            "Timestamp field argument, got Bool",
            "for a test of the group write `all(o.paid for o in group)`",
        ),
        (
            "min(orders.paid)",
            "min",
            "PIE-S2314",
            "Aggregate function min expects Int, Float, Decimal, Date, or "
            "Timestamp field argument, got Bool",
            "for a test of the group write `all(o.paid for o in group)`",
        ),
    ],
)
def test_each_refused_group_test_reports_its_first_broken_rule(
    call: str, at: str, code: str, message: str, hint: str | None
) -> None:
    result = _analyze(_grouped(call))

    text = message if hint is None else f"{message}; {hint}"
    assert _rows(result) == [(code, "error", LINE, _at(at, call), text, hint)]


@pytest.mark.parametrize(
    ("call", "hint"),
    [
        ("any(r.price for r in group)", "such as `r.price > 0`"),
        ("all(o.price for o in group)", "such as `o.price > 0`"),
        ("any(o.status for o in group)", "such as a comparison"),
        ("all(o.amount for o in group)", "such as a comparison"),
        ("all(o.price + 1 for o in group)", "such as a comparison"),
    ],
)
def test_a_group_test_body_that_is_no_bool_suggests_a_test(
    call: str, hint: str
) -> None:
    """The message keeps the relation `any` text; only the suggestion asks for
    a test, naming a number field (`amount` is a `Cents` alias)."""
    name, _, rest = call.partition("(")
    body = rest.partition(" for ")[0]

    assert _rows(_analyze(_grouped(call))) == [
        (
            "PIE-S2202",
            "error",
            LINE,
            _at(body, call),
            f"Expected Bool expression in {name.upper()} predicate",
            f"write the body as a test, {hint}",
        )
    ]


@pytest.mark.parametrize(
    ("call", "hint"),
    [
        ("all(paid)", "write `all(o.paid for o in group)`"),
        ("ALL(paid)", "write `all(o.paid for o in group)`"),
        ("every(paid)", "write `all(o.paid for o in group)`"),
        ("bool_and(orders.paid)", "write `all(o.paid for o in group)`"),
        ("any(paid)", "write `any(o.paid for o in group)`"),
        ("bool_or(paid)", "write `any(o.paid for o in group)`"),
        ("any(paid, amount)", "write `any(o.x for o in group)`"),
        # A relation is no member field.
        ("all(orders)", "write `all(o.x for o in group)`"),
    ],
)
def test_a_group_test_habit_names_the_generator(call: str, hint: str) -> None:
    name = call.partition("(")[0]

    assert _rows(_analyze(_grouped(call))) == [
        ("PIE-S2103", "error", LINE, 29, f"Unknown function: {name}; {hint}", hint),
        (
            "PIE-S2319",
            "error",
            LINE,
            29,
            "Grouped scalar projection expressions are not supported yet",
            None,
        ),
    ]


@pytest.mark.parametrize(
    ("clause", "hint"),
    [
        ("    select a = all(c.id)\n", "write `all(o.id for o in group)`"),
        (
            "    where all(c.id)\n    select x = c.id\n",
            "write `all(o.id for o in group)`",
        ),
        ("    select a = any(paid)\n", "write `any(o.paid for o in group)`"),
        ("    select a = all(orders)\n", "write `all(o.x for o in group)`"),
    ],
)
def test_a_project_group_test_habit_over_join_rows_names_its_field(
    tmp_path, capsys, clause: str, hint: str
) -> None:
    """A project types each field read of a JOIN's row before the call, so its
    hint names the field as a file's does; a relation is still `o.x`."""
    import json

    from pietto import cli

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (tmp_path / "main.pietto").write_text(
        PREFIX + "query q:\n    from orders\n    let c = customers\n"
        "    inner join c on c.id == orders.customer_id\n" + clause
    )
    found = []
    for argv in (
        ["check", "--project", str(tmp_path), "--format", "json"],
        ["check", str(tmp_path / "main.pietto"), "--format", "json"],
    ):
        assert cli.main(argv) == 1
        found.append(
            [
                (
                    row["code"],
                    row["location"]["line"],
                    row["message"],
                    row["suggestion"],
                )
                for row in json.loads(capsys.readouterr().out)["diagnostics"]
            ]
        )
    assert found[0] == found[1]
    assert [(row[0], row[3]) for row in found[0]] == [("PIE-S2103", hint)]


@pytest.mark.parametrize(
    ("clause", "column", "code", "message", "hint"),
    [
        (
            "    where any(o.paid for o in group)\n",
            31,
            "PIE-S2301",
            "Unknown or unavailable ANY relation: group",
            _BEFORE,
        ),
        (
            "    where all(o.paid for o in group)\n",
            11,
            "PIE-S2308",
            "Aggregate all() is not allowed in where clause; use it only as a "
            f"direct aliased select projection; {_BEFORE}",
            _BEFORE,
        ),
        (
            "    let z = any(o.paid for o in group)\n",
            33,
            "PIE-S2301",
            "Unknown or unavailable ANY relation: group",
            _BEFORE,
        ),
        (
            "    let z = all(o.paid for o in group)\n",
            13,
            "PIE-S2308",
            "Aggregate all() is not allowed in let binding; use it only as a "
            f"direct aliased select projection; {_BEFORE}",
            _BEFORE,
        ),
    ],
)
def test_a_group_test_before_group_by_says_there_is_no_group(
    clause: str, column: int, code: str, message: str, hint: str
) -> None:
    result = _analyze(
        f"query q:\n    from orders\n{clause}    group by customer_id\n"
        "    select customer_id, n = count()\n"
    )

    assert _rows(result) == [
        (code, "error", PREFIX.count("\n") + 3, column, message, hint)
    ]


@pytest.mark.parametrize(
    ("clause", "context"), [("having", "having clause"), ("order by", "order by")]
)
def test_a_group_test_in_having_or_order_by_says_to_select_it(
    clause: str, context: str
) -> None:
    query = (
        "query q:\n    from orders\n    group by customer_id\n"
        "    select customer_id, c = count()\n    {} {}(o.paid for o in {})\n"
    )
    selected = {
        name: f"select `{output} = {name}(o.paid for o in group)` and read "
        f"`{output}` in `having` or `order by`"
        for name, output in (("any", "has_paid"), ("all", "all_paid"))
    }

    assert [
        (item.code, item.message, item.suggestion)
        for name, source in (("any", "group"), ("any", "orders"), ("all", "group"))
        for item in _analyze(query.format(clause, name, source)).diagnostics
    ] == [
        ("PIE-S2334", "ANY is not supported in this context", selected["any"]),
        ("PIE-S2334", "ANY is not supported in this context", None),
        (
            "PIE-S2308",
            f"Aggregate all() is not allowed in {context}; use it only as a "
            f"direct aliased select projection; {selected['all']}",
            selected["all"],
        ),
    ]


@pytest.mark.parametrize(
    "select",
    [
        "    group by customer_id\n    select customer_id, c = count()\n",
        "    select id\n",
    ],
    ids=("grouped", "no_group_by"),
)
def test_a_group_test_in_qualify_has_no_having_hint(select: str) -> None:
    """QUALIFY reads no selected test of the group."""
    result = _analyze(
        f"query q:\n    from orders\n{select}    qualify any(o.paid for o in group)\n"
    )

    assert [
        (item.code, item.message, item.suggestion) for item in result.diagnostics
    ] == [("PIE-S2334", "ANY is not supported in this context", None)]


@pytest.mark.parametrize(
    ("select", "column"),
    [
        ("    group by customer_id\n    select customer_id, n = {}\n", 29),
        ("    select n = {}\n", 16),
        ("    select id, n = {}\n", 20),
        ("    select c = count(), n = {}\n", 29),
    ],
    ids=("grouped", "alone", "beside_a_field", "beside_an_aggregate"),
)
@pytest.mark.parametrize("name", ["any", "all"])
def test_a_select_item_refuses_a_group_test_over_a_relation_named_group(
    select: str, column: int, name: str
) -> None:
    """In a SELECT item `for o in group` could mean the group or the relation,
    so a relation named `group` there is refused with a rename hint; WHERE
    keeps its relation meaning."""
    source = (
        PREFIX.replace(
            "source customers:",
            'source group: Order = postgres.table("shop.g")\nsource customers:',
        )
        + "query tests:\n    from customers\n"
        "    where any(o.customer_id == customers.id for o in group)\n"
        "    select id\n"
        + "query q:\n    from orders\n"
        + select.format(f"{name}(o.paid for o in group)")
    )
    parsed = parse_source(source)
    assert parsed.ast is not None

    assert _rows(analyze(parsed.ast)) == [
        (
            "PIE-S2334",
            "error",
            source.count("\n"),
            column + len(name) + 17,
            f"Generator over group in {name}: group is the relation group, not "
            f"this group; {_RENAME}",
            _RENAME,
        )
    ]


def test_a_let_named_group_is_refused_in_a_group_test() -> None:
    result = _analyze(
        "query q:\n    let group = customers\n    from orders\n"
        "    group by customer_id\n"
        "    select customer_id, n = any(o.paid for o in group)\n"
    )

    hint = "rename the let group to read this group's rows"
    assert _rows(result) == [
        (
            "PIE-S2334",
            "error",
            PREFIX.count("\n") + 5,
            49,
            f"Generator over group in any: group is the let group, not this group; "
            f"{hint}",
            hint,
        )
    ]


def test_a_group_test_over_join_rows_is_refused_with_a_hint() -> None:
    result = _analyze(
        "query q:\n    from orders\n"
        "    inner join customers on orders.customer_id == customers.id\n"
        "    group by orders.customer_id\n"
        "    select customer_id, n = all(o.paid for o in group)\n"
    )

    hint = "join in one query, then group it in another that reads it with `from`"
    assert [
        (item.code, item.message, item.suggestion) for item in result.diagnostics
    ] == [
        (
            "PIE-S2334",
            "all(... for o in group ...) over JOIN rows is not available yet; " + hint,
            hint,
        )
    ]


@pytest.mark.parametrize(
    ("name", "suggestion"),
    [
        (
            "any",
            "Rename this def: `any` is the built-in test of a relation or of a "
            "group, and a call to any always means it.",
        ),
        (
            "all",
            "Rename this def: `all` is now the built-in test of a group, and a "
            "call to all always means it.",
        ),
    ],
)
def test_a_def_named_any_or_all_is_refused_with_a_rename(
    name: str, suggestion: str
) -> None:
    result = _analyze(
        f"def {name}(x: Int) -> Int:\n    return x + 1\n"
        f"query q:\n    from orders\n    select id, y = {name}(amount)\n"
    )

    assert [
        (item.code, item.location.line, item.message, item.suggestion)
        for item in result.diagnostics
    ] == [
        (
            "PIE-S2398",
            PREFIX.count("\n") + 1,
            f"Def {name} has the name of a built-in function; a def cannot shadow one",
            suggestion,
        )
    ]


def test_a_group_test_inherits_the_not_in_warning_of_where() -> None:
    """TEST is read as WHERE reads it: a `not in` over a nullable field is
    never True for None, as the WHERE conjunct `status is not None` says."""
    call = 'any(o.status not in ("a", "b") for o in group)'
    warned = _analyze(_grouped(call))
    silenced = _analyze(
        _grouped(call).replace(
            "    group by", "    where status is not None\n    group by"
        )
    )

    assert [(item.code, item.severity) for item in warned.diagnostics] == [
        ("PIE-S2384", Severity.WARNING)
    ]
    assert silenced.diagnostics == ()


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
