"""The single-file fan-out rule for aggregates over JOIN rows.

The facts each relation's rule reads are the ones the analyzer builds from its
file. The queries named faN are admitted and those named frN refused; the
others name the case they pin. Each JOIN names its input with `let` and
states its match in `on`, through a shape-typed relationship call where a
declared key proves it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from _pietto_semantic_join_facts import JoinScript, join_script, located
from pietto._project import check as project_check
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze

_FANOUT_SOURCE: str = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
    rush: Bool
    order_key = unique(id)
shape OrderX:
    id: Int
    customer_id: Int | None
    amount: Int
    ox_key = unique(id)
    ox_cust = unique(customer_id)
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
    vip: Bool
    customer_key = unique(id)
shape Region:
    id: Int
    label: Text
    region_key = unique(id)
shape Line:
    ord_id: Int
    line_no: Int
    qty: Int
    line_k = unique(ord_id, line_no)
shape Ship:
    id: Int
    ord_id: Int | None
    line_no: Int | None
    qty: Int | None
    ship_k = unique(id)
shape Cust:
    id: Int
    ref: Int | None
    cust_k0 = unique(id)
shape Ord:
    id: Int
    cust_id: Int | None
source orders: Order = postgres.table("shop.orders")
source orders_x: OrderX = postgres.table("shop.orders_x")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
source lines: Line = postgres.table("shop.lines")
source ships: Ship = postgres.table("shop.ships")
source cust: Cust = postgres.table("app.cust")
source ord: Ord = postgres.table("app.ord")
relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id
relationship customer_region(customer: Customer, region: Region): customer.region_id == region.id
relationship ox_customer(order: OrderX, customer: Customer): order.customer_id == customer.id
relationship ship_line(ship: Ship, line: Line): ship.ord_id == line.ord_id and ship.line_no == line.line_no
relationship ship_order(ship: Ship, line: Line): ship.ord_id == line.ord_id
relationship ship_line_qty(ship: Ship, line: Line):
    ship.ord_id == line.ord_id and ship.line_no == line.line_no and ship.qty == line.qty
relationship referral(referrer: Cust, referee: Cust): referrer.ref == referee.id
relationship ord_cust(o: Ord, c: Cust): o.cust_id == c.id
query named_customers:
    from customers
    where name != ""
    select:
        id
        name
query totals:
    from orders
    select:
        total = count()
query fa1:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    group by customer.id, customer.name
    select:
        name = customer.name
        biggest = max(orders.amount)
        n = count()
query fa2:
    from customers
    let o = orders
    inner join o on order_customer(o, customers)
    select:
        biggest = max(o.amount)
query fa3:
    from customers
    let o = orders
    inner join o on order_customer(o, customers)
    group by customers.id
    select:
        total = count(o.id)
query fa4:
    from orders
    let c = customers
    left join c on order_customer(orders, c)
    select:
        n = count(orders.id)
query fa5:
    from orders
    let r = regions
    cross join r
    select:
        n = count()
query fa6:
    from cust
    let b2 = cust
    inner join b2 on referral(b2, cust)
    select:
        mn = min(b2.id)
query fa7:
    from customers
    let o = orders
    left join o on order_customer(o, customers)
    group by o.id
    select:
        oid = o.id
        n = count(customers.id)
query fa8:
    from orders
    let c = customers
    right join c on orders.customer_id == c.id
    group by orders.id
    select:
        oid = orders.id
        n = count(c.id)
query fa9:
    from ships
    let l = lines
    inner join l on ship_line(ships, l)
    select:
        n = count(ships.id)
query fa10:
    from lines
    let s = ships
    inner join s on ship_line(s, lines)
    select:
        m = max(s.id)
query fa11:
    from customers
    let r = regions
    inner join r on r.id >= customers.region_id
    let o = orders
    inner join o on order_customer(o, customers) and o.amount > 0
    group by r.id
    select:
        rid = r.id
        n = count(o.id)
query fa12:
    from cust
    let b1 = cust
    where any(referral(cust, b1) for b1 in b1)
    let b2 = cust
    inner join b2 on referral(b2, cust) and b2.ref != 5
    select:
        mn = min(b2.id)
query fa13:
    from cust
    let b2 = cust
    inner join b2 on referral(b2, cust) and b2.ref != 5
    select:
        mn = min(b2.id)
query fa14:
    from cust
    let b2 = ord
    inner join b2 on ord_cust(b2, cust) and b2.id != 5
    select:
        mn = min(b2.id)
query fr1:
    from customers
    let o = orders
    inner join o on o.customer_id == customers.id
    group by customers.name
    select:
        name = customers.name
        cnt = count(customers.id)
query fr2:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    select:
        n = count(c.name)
query fr3:
    from orders
    let r = regions
    cross join r
    select:
        n = count(orders.id)
query fr4:
    from orders
    let c = named_customers
    inner join c on orders.customer_id == c.id
    select:
        n = count(orders.id)
query fr5:
    from orders
    let t = totals
    cross join t
    group by orders.customer_id
    select:
        m = max(orders.amount)
query fr6:
    from orders
    let c = customers
    right join c on order_customer(orders, c)
    let r = regions
    left join r on customer_region(c, r)
    group by orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr7:
    from orders
    let c = customers
    right join c on order_customer(orders, c)
    let r = regions
    cross join r
    group by orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr8:
    from orders
    let c = customers
    full join c on order_customer(orders, c)
    let r = regions
    cross join r
    group by orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr9:
    from customers
    let r = regions
    right join r on customer_region(customers, r)
    let w = orders
    cross join w
    select:
        n = count(customers.vip or w.rush)
query fr10:
    from customers
    let r = regions
    inner join r on r.id >= customers.region_id
    let o = orders
    right join o on order_customer(o, customers)
    group by r.id
    select:
        rid = r.id
        n = count(o.id)
query fr14:
    from cust
    let b2 = cust
    right join b2 on referral(b2, cust)
    select:
        mn = min(b2.id)
query fr15:
    from customers
    let o = orders_x
    inner join o on o.amount == customers.id
    group by o.customer_id
    select:
        n = count(customers.id)
query fr16:
    from ships
    let l = lines
    inner join l on ship_order(ships, l)
    select:
        n = count(ships.id)
query fr17:
    from orders_x
    let c = customers
    right join c on ox_customer(orders_x, c)
    select:
        n = count(c.id)
query count_only:
    from orders
    let r = regions
    cross join r
    select:
        n = count()
query not_exempt:
    from orders
    let r = regions
    cross join r
    select:
        n = count()
        low = min(r.id)
        high = max(r.id)
        labels = count_distinct(r.label)
        k = count(r.id)
query chain_admitted:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    let r = regions
    left join r on customer_region(c, r)
    select:
        n = count(orders.id)
query chain_refused:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    let r = regions
    left join r on customer_region(c, r)
    select:
        top = max(r.id)
query let_argument:
    from orders
    let r = regions
    cross join r
    let label_text = r.label
    let shown = label_text
    select:
        n = count(shown)
query let_admitted:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    let paid = orders.amount
    select:
        total = sum(paid)
query renamed_key:
    from customers
    let o = orders
    inner join o on o.customer_id == customers.id
    let cid = customers.id
    group by cid
    select:
        total = count(o.id)
query renamed_non_key:
    from customers
    let o = orders
    inner join o on o.amount == customers.region_id
    let cname = customers.name
    group by cname
    select:
        total = count(o.id)
query reverse_subset:
    from lines
    let s = ships
    inner join s on ship_line_qty(s, lines)
    select:
        m = max(s.id)
query semi_not_factor:
    from customers
    let o = orders
    where not any(order_customer(o, customers) for o in o)
    let r = regions
    inner join r on customer_region(customers, r)
    select:
        n = count(customers.id)
query one_key_two_joins:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    let d = customers
    inner join d on order_customer(orders, d)
    select:
        n = count(c.name)
query composite_key_text:
    from lines
    let s = ships
    inner join s on ship_line(s, lines)
    select:
        n = count(lines.ord_id)
query two_keys:
    from orders
    let c = customers
    inner join c on order_customer(orders, c)
    let r = regions
    inner join r on customer_region(c, r)
    select:
        n = count(r.label)
query unique_keys_of_two:
    from orders
    let r = regions
    cross join r
    let k = customers
    cross join k
    select:
        n = count(orders.id)
"""


@pytest.fixture(scope="module")
def fanout() -> JoinScript:
    return join_script(_FANOUT_SOURCE)


def _at(query: str, needle: str) -> tuple[int, int]:
    """The 1-based line and column of the first `needle` inside a query."""

    lines = _FANOUT_SOURCE.split("\n")
    start = lines.index(f"query {query}:")
    for number, line in enumerate(lines[start:], start + 1):
        if needle in line:
            return number, line.index(needle) + 1
    raise AssertionError(f"{needle!r} is not in query {query}")


_ADMITTED = (
    "fa1",
    "fa2",
    "fa3",
    "fa4",
    "fa5",
    "fa6",
    "fa7",
    "fa8",
    "fa9",
    "fa10",
    "fa11",
    "fa12",
    "fa13",
    "fa14",
    "count_only",
    "chain_admitted",
    "let_admitted",
    "renamed_key",
    "reverse_subset",
    "semi_not_factor",
)


@pytest.mark.parametrize("query", _ADMITTED)
def test_an_aggregate_whose_inputs_determine_every_input_row_is_admitted(
    fanout: JoinScript, query: str
) -> None:
    """A relationship call that is a required conjunct of an INNER `on` proves
    the rows of each side whose declared key it matches (fa1, fa2, fa6, fa9,
    fa10 and a key smaller than the matched fields), also beside further
    filters of the same `on` (fa11 to fa14); of a LEFT `on` it proves the
    joined side (fa4 and a chain). Strict group keys (fa3, fa7, fa8 and a
    renamed key), `count()` (fa1, fa5), `let` arguments, and the hidden SEMI
    or ANTI JOIN of a JOIN-prefix `[not] any` (fa12, semi_not_factor), which
    repeats no row, need no proof."""

    assert fanout.fanout(query) == ()


def _repeated(joins: str = "", remedy: str = "") -> str:
    cause = f"rows repeated by {joins}" if joins else "rows that a JOIN repeats"
    return f"An aggregate may read {cause}" + (f"; {remedy}" if remedy else "")


def _match(*bindings: str) -> str:
    noun = "a unique key" if len(bindings) == 1 else "unique keys"
    return (
        f"match {noun} of {' and '.join(bindings)} in "
        "`on`, use `any(...)` for an input that only filters rows, or aggregate "
        "in a separate query first"
    )


_REFUSED = (
    # The hand-written equality matches the key of customers, not of o.
    ("fr1", "count(customers.id)", _repeated("JOIN o", _match("o"))),
    # The call matches the key of c, not of orders.
    ("fr2", "count(c.name)", _repeated("JOIN c", _match("orders"))),
    ("fr3", "count(orders.id)", _repeated("JOIN r", _match("r"))),
    # A query carries no declared key in a single file.
    ("fr4", "count(orders.id)", _repeated("JOIN c")),
    ("fr5", "max(orders.amount)", _repeated("JOIN t")),
    # RIGHT and FULL calls prove nothing: a NULL-extended row of one side
    # determines no row of the other.
    ("fr6", "count(r.id)", _repeated("JOIN c and JOIN r", _match("c"))),
    ("fr7", "count(r.id)", _repeated("JOIN c", _match("c"))),
    ("fr8", "count(r.id)", _repeated("JOIN c", _match("c"))),
    ("fr9", "count(customers.vip or w.rush)", _repeated("JOIN r", _match("r"))),
    ("fr10", "count(o.id)", _repeated("JOIN r and JOIN o", _match("customers"))),
    ("fr14", "min(b2.id)", _repeated("JOIN b2", _match("cust"))),
    # A nullable key protects no group, and the equality matches no key of o.
    ("fr15", "count(customers.id)", _repeated("JOIN o", _match("o"))),
    # A composite key covered only in part.
    ("fr16", "count(ships.id)", _repeated("JOIN l", _match("l"))),
    ("fr17", "count(c.id)", _repeated("JOIN c", _match("orders_x"))),
    ("chain_refused", "max(r.id)", _repeated("JOIN r", _match("orders"))),
    # The argument reads r through two `let` names, and the group key is a
    # renamed field that is no key (the equality matches no key of customers).
    ("let_argument", "count(shown)", _repeated("JOIN r", _match("orders"))),
    ("renamed_non_key", "count(o.id)", _repeated("JOIN o", _match("customers"))),
    # One key serves two JOINs; a composite key; two keys; two group keys.
    ("one_key_two_joins", "count(c.name)", _repeated("JOIN c", _match("orders"))),
    ("composite_key_text", "count(lines.ord_id)", _repeated("JOIN s", _match("s"))),
    ("two_keys", "count(r.label)", _repeated("JOIN r", _match("orders"))),
    (
        "unique_keys_of_two",
        "count(orders.id)",
        _repeated("JOIN r and JOIN k", _match("r", "k")),
    ),
)


@pytest.mark.parametrize(
    ("query", "call", "message"), _REFUSED, ids=[case[0] for case in _REFUSED]
)
def test_an_aggregate_that_may_read_repeated_rows_is_refused_at_its_call(
    fanout: JoinScript, query: str, call: str, message: str
) -> None:
    diagnostics = fanout.fanout(query)
    assert all(item.severity is Severity.ERROR for item in diagnostics)
    assert located(diagnostics) == [("PIE-S2381", message, *_at(query, call))]


def test_only_count_without_an_argument_is_exempt(fanout: JoinScript) -> None:
    """`min`, `max`, `count_distinct` and `count` of a field read the rows a
    JOIN repeats; each is refused once, in select order."""

    message = _repeated("JOIN r", _match("orders"))
    assert located(fanout.fanout("not_exempt")) == [
        ("PIE-S2381", message, *_at("not_exempt", call))
        for call in ("min(r.id)", "max(r.id)", "count_distinct(r.label)", "count(r.id)")
    ]


def test_an_aggregate_that_reads_no_input_names_no_repeated_join() -> None:
    """Its rows are repeated by every JOIN at once (single files also refuse
    the argument with PIE-S2315)."""

    source = (
        _FANOUT_SOURCE.split("query named_customers:")[0]
        + "query no_field:\n    from orders\n    let r = regions\n    cross join r\n"
        "    select:\n        n = sum(1)\n"
    )
    facts = join_script(source)
    lines = source.split("\n")
    line = lines.index("        n = sum(1)") + 1
    assert located(facts.fanout("no_field")) == [
        ("PIE-S2381", _repeated(remedy=_match("orders", "r")), line, 13)
    ]


# Where both modes refuse an aggregate for fan-out, the single-file message is
# the project's cause clause: the JOINs that repeat its rows and the inputs
# whose keys the remedy matches; the project accepts the refusals in which
# single files are stricter.
_SAME_REMEDY = (
    ("fr1", "JOIN o", "o"),
    ("fr2", "JOIN c", "orders"),
    ("fr3", "JOIN r", "r"),
    ("fr6", "JOIN c and JOIN r", "c"),
    ("fr7", "JOIN c", "c"),
    ("fr8", "JOIN c", "c"),
    ("fr9", "JOIN r", "r"),
    ("fr15", "JOIN o", "o"),
    ("fr16", "JOIN l", "l"),
    ("not_exempt", "JOIN r", "orders"),
    ("chain_refused", "JOIN r", "orders"),
    ("let_argument", "JOIN r", "orders"),
    ("renamed_non_key", "JOIN o", "customers"),
    ("one_key_two_joins", "JOIN c", "orders"),
    ("composite_key_text", "JOIN s", "s"),
    ("two_keys", "JOIN r", "orders"),
    ("unique_keys_of_two", "JOIN r and JOIN k", "r and k"),
)
# The project proves RIGHT JOINs and JOINs to a query that the bounded
# single-file rule deliberately leaves unproven; it carries the key of
# customers through the query `named_customers`, which the hand-written
# equality of fr4 matches.
_STRICTER = ("fr4", "fr5", "fr10", "fr14", "fr17")


def test_fanout_messages_are_the_project_cause_clause(
    fanout: JoinScript, tmp_path: Path
) -> None:
    root = tmp_path / "fanout"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_FANOUT_SOURCE, encoding="utf-8")
    project = build_project_completed_semantic_result(
        build_empty_project_semantic_result(
            project_check.check_project_parse_only(root)
        )
    )
    clauses: dict[str, str] = {}
    for item in project.diagnostics:
        match = re.fullmatch(
            r"Project relation semantic completion is unavailable: (\w+) \((.*)\)",
            item.message,
        )
        assert item.code == "PIE-S2333" and match is not None, item
        clauses[match.group(1)] = match.group(2)
    names = tuple(query for query, _, _ in _SAME_REMEDY)
    assert tuple(clauses) == names
    for query, joins, bindings in _SAME_REMEDY:
        message = _repeated(joins, _match(*bindings.split(" and ")))
        assert clauses[query] == "a" + message[1:]
        assert {item.message for item in fanout.fanout(query)} == {message}
    for query in (*_STRICTER, *_ADMITTED):
        assert query not in clauses


@pytest.mark.parametrize("protected", ("customers", "peer"))
def test_analyzer_keeps_each_aggregate_and_self_binding_separate(
    protected: str,
) -> None:
    other = "peer" if protected == "customers" else "customers"
    source = (
        _FANOUT_SOURCE.split("query named_customers:")[0]
        + f"""query grouped:
    from customers
    let peer = customers
    cross join peer
    let first_key = {protected}.id
    let group_key = first_key
    let first_value = {protected}.id
    let repeated_value = first_value
    group by group_key
    select:
        key = {protected}.id
        once = count({other}.id)
        repeated = count(repeated_value)
"""
    )
    parsed = parse_source(source, path="fanout-bindings.pietto")
    assert parsed.ast is not None, parsed.diagnostics
    result = analyze(parsed.ast)
    line = source.splitlines().index("        repeated = count(repeated_value)") + 1
    assert located(result.diagnostics) == [
        ("PIE-S2381", _repeated("JOIN peer", _match(other)), line, 20)
    ]


@pytest.mark.parametrize("grouped", ("r", "c"))
def test_refined_left_subtree_cannot_determine_an_earlier_cross_input(
    grouped: str,
) -> None:
    source = (
        _FANOUT_SOURCE.split("query named_customers:")[0]
        + f"""query refined:
    from orders
    let r = regions
    cross join r
    let c = customers
    left join c on order_customer(orders, c) and r.id == c.region_id
    let x = orders_x
    inner join x on ox_customer(x, c)
    group by {grouped}.id
    select:
        n = count(orders.id)
"""
    )
    parsed = parse_source(source, path="fanout-refined.pietto")
    assert parsed.ast is not None, parsed.diagnostics
    result = analyze(parsed.ast)
    expected = (
        []
        if grouped == "r"
        else [
            (
                "PIE-S2381",
                _repeated("JOIN r and JOIN c", _match("r")),
                source.splitlines().index("        n = count(orders.id)") + 1,
                13,
            )
        ]
    )
    assert located(result.diagnostics) == expected
