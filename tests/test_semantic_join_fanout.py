"""The single-file fan-out rule for aggregates over JOIN rows.

The facts each relation's rule reads are built from its file as the analyzer
builds them. The queries named faN are admitted and those named frN refused;
the others name the case they pin.
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
    id: Int not null
    customer_id: Int nullable
    amount: Int not null
    rush: Bool not null
    unique order_key on id
shape OrderX:
    id: Int not null
    customer_id: Int nullable
    amount: Int not null
    unique ox_key on id
    unique ox_cust on customer_id
shape Customer:
    id: Int not null
    name: Text not null
    region_id: Int nullable
    vip: Bool not null
    unique customer_key on id
shape Region:
    id: Int not null
    label: Text not null
    unique region_key on id
shape Line:
    ord_id: Int not null
    line_no: Int not null
    qty: Int not null
    unique line_k on ord_id, line_no
shape Ship:
    id: Int not null
    ord_id: Int nullable
    line_no: Int nullable
    qty: Int nullable
    unique ship_k on id
shape Cust:
    id: Int not null
    ref: Int nullable
    unique cust_k0 on id
shape Ord:
    id: Int not null
    cust_id: Int nullable
source orders: Order is postgres.table("shop.orders")
source orders_x: OrderX is postgres.table("shop.orders_x")
source customers: Customer is postgres.table("shop.customers")
source regions: Region is postgres.table("shop.regions")
source lines: Line is postgres.table("shop.lines")
source ships: Ship is postgres.table("shop.ships")
source cust: Cust is postgres.table("app.cust")
source ord: Ord is postgres.table("app.ord")
relationship order_customer: orders.customer_id == customers.id
relationship customer_region: customers.region_id == regions.id
relationship ox_customer: orders_x.customer_id == customers.id
relationship ship_line: ships.ord_id == lines.ord_id and ships.line_no == lines.line_no
relationship ship_order: ships.ord_id == lines.ord_id
relationship ship_line_qty: ships.ord_id == lines.ord_id and ships.line_no == lines.line_no and ships.qty == lines.qty
relationship referral:
    endpoint referrer: cust
    endpoint referee: cust
    on referrer.ref == referee.id
relationship ord_cust:
    endpoint o: ord
    endpoint c: cust
    on o.cust_id == c.id
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
    inner join customers as customer
    group by: customer.id, customer.name
    select:
        name = customer.name
        biggest = max(orders.amount)
        n = count()
query fa2:
    from customers
    inner join orders as o
    select:
        biggest = max(o.amount)
query fa3:
    from customers
    inner join orders as o
    group by: customers.id
    select:
        total = count(o.id)
query fa4:
    from orders
    left join customers as c
    select:
        n = count(orders.id)
query fa5:
    from orders
    cross join regions as r: from orders
    select:
        n = count()
query fa6:
    from cust
    inner join cust as b2:
        from cust
        via referral: referee -> referrer
    select:
        mn = min(b2.id)
query fa7:
    from customers
    left join orders as o
    group by: o.id
    select:
        oid = o.id
        n = count(customers.id)
query fa8:
    from orders
    right join customers as c:
        from orders
        on orders.customer_id == c.id
    group by: orders.id
    select:
        oid = orders.id
        n = count(c.id)
query fa9:
    from ships
    inner join lines as l: via ship_line
    select:
        n = count(ships.id)
query fa10:
    from lines
    inner join ships as s: via ship_line
    select:
        m = max(s.id)
query fr1:
    from customers
    inner join orders as o:
        from customers
        on o.customer_id == customers.id
    group by: customers.name
    select:
        name = customers.name
        cnt = count(customers.id)
query fr2:
    from orders
    inner join customers as c
    select:
        n = count(c.name)
query fr3:
    from orders
    cross join regions as r: from orders
    select:
        n = count(orders.id)
query fr4:
    from orders
    inner join named_customers as c:
        from orders
        on orders.customer_id == c.id
    select:
        n = count(orders.id)
query fr5:
    from orders
    cross join totals as t: from orders
    group by: orders.customer_id
    select:
        m = max(orders.amount)
query fr6:
    from orders
    right join customers as c
    left join regions as r: from c
    group by: orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr7:
    from orders
    right join customers as c
    cross join regions as r: from orders
    group by: orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr8:
    from orders
    full join customers as c
    cross join regions as r: from orders
    group by: orders.id
    select:
        oid = orders.id
        n = count(r.id)
query fr9:
    from customers
    right join regions as r
    cross join orders as w: from customers
    select:
        n = count(customers.vip or w.rush)
query fr10:
    from customers
    inner join regions as r:
        from customers
        on r.id >= customers.region_id
    right join orders as o: from customers
    group by: r.id
    select:
        rid = r.id
        n = count(o.id)
query fr11:
    from customers
    inner join regions as r:
        from customers
        on r.id >= customers.region_id
    inner join orders as o:
        from customers
        via order_customer
        on o.amount > 0
    group by: r.id
    select:
        rid = r.id
        n = count(o.id)
query fr12:
    from cust
    semi join cust as b1:
        from cust
        via referral: referrer -> referee
    inner join cust as b2:
        from cust
        via referral: referee -> referrer
        on b2.ref != 5
    select:
        mn = min(b2.id)
query fr13:
    from cust
    inner join cust as b2:
        from cust
        via referral: referee -> referrer
        on b2.ref != 5
    select:
        mn = min(b2.id)
query fr14:
    from cust
    right join cust as b2:
        from cust
        via referral: referee -> referrer
    select:
        mn = min(b2.id)
query fr15:
    from customers
    inner join orders_x as o:
        from customers
        on o.customer_id == customers.id
    group by: o.customer_id
    select:
        n = count(customers.id)
query fr16:
    from ships
    inner join lines as l: via ship_order
    select:
        n = count(ships.id)
query fr17:
    from orders_x
    right join customers as c
    select:
        n = count(c.id)
query fr18:
    from cust
    inner join ord as b2:
        from cust
        via ord_cust: c -> o
        on b2.id != 5
    select:
        mn = min(b2.id)
query count_only:
    from orders
    cross join regions as r: from orders
    select:
        n = count()
query not_exempt:
    from orders
    cross join regions as r: from orders
    select:
        n = count()
        low = min(r.id)
        high = max(r.id)
        labels = count_distinct(r.label)
        k = count(r.id)
query chain_admitted:
    from orders
    inner join customers as c
    left join regions as r: from c
    select:
        n = count(orders.id)
query chain_refused:
    from orders
    inner join customers as c
    left join regions as r: from c
    select:
        top = max(r.id)
query let_argument:
    from orders
    cross join regions as r: from orders
    let:
        label_text = r.label
        shown = label_text
    select:
        n = count(shown)
query let_admitted:
    from orders
    inner join customers as c
    let:
        paid = orders.amount
    select:
        total = sum(paid)
query renamed_key:
    from customers
    inner join orders as o:
        from customers
        on o.customer_id == customers.id
    let:
        cid = customers.id
    group by: cid
    select:
        cid
        total = count(o.id)
query renamed_non_key:
    from customers
    inner join orders as o:
        from customers
        on o.customer_id == customers.id
    let:
        cname = customers.name
    group by: cname
    select:
        cname
        total = count(o.id)
query reverse_subset:
    from lines
    inner join ships as s: via ship_line_qty
    select:
        m = max(s.id)
query semi_not_factor:
    from customers
    anti join orders as o
    select:
        n = count(customers.id)
query one_key_two_joins:
    from orders
    inner join customers as c
    inner join customers as d: from orders
    select:
        n = count(c.name)
query composite_key_text:
    from lines
    inner join ships as s: via ship_line
    select:
        n = count(lines.ord_id)
query two_keys:
    from orders
    inner join customers as c
    inner join regions as r: from c
    select:
        n = count(r.label)
query unique_keys_of_two:
    from orders
    cross join regions as r: from orders
    cross join customers as k: from orders
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
    """Forward edges of INNER and LEFT relationship JOINs (fa1, fa4, fa9 and a
    chain), reverse edges of INNER M1/M2 JOINs (fa2, fa6, fa10, and a source
    key smaller than the matched fields), strict group keys (fa3, fa7, fa8 and
    a renamed key), `count()` (fa1, fa5), `let:` arguments, and SEMI or ANTI
    targets, which repeat no row."""

    assert fanout.fanout(query) == ()


def _repeated(joins: str, remedy: str = "") -> str:
    return f"An aggregate may read rows repeated by {joins}" + (
        f"; {remedy}" if remedy else ""
    )


def _group(binding: str) -> str:
    return f"group by a unique key of {binding} whose fields are all not null"


_REFUSED = (
    ("fr1", "count(customers.id)", _repeated("JOIN o", _group("o"))),
    (
        "fr2",
        "count(c.name)",
        _repeated(
            "JOIN c",
            "declare a unique key on orders.customer_id (matched by JOIN c), or "
            + _group("orders"),
        ),
    ),
    ("fr3", "count(orders.id)", _repeated("JOIN r", _group("r"))),
    ("fr4", "count(orders.id)", _repeated("JOIN c")),
    ("fr5", "max(orders.amount)", _repeated("JOIN t")),
    # RIGHT and FULL JOINs give no edge: a NULL-extended source part
    # determines no target row.
    ("fr6", "count(r.id)", _repeated("JOIN c and JOIN r", _group("c"))),
    ("fr7", "count(r.id)", _repeated("JOIN c", _group("c"))),
    ("fr8", "count(r.id)", _repeated("JOIN c", _group("c"))),
    ("fr9", "count(customers.vip or w.rush)", _repeated("JOIN r", _group("r"))),
    # Neither do the reverse directions of RIGHT and M4 JOINs.
    ("fr10", "count(o.id)", _repeated("JOIN r and JOIN o", _group("customers"))),
    ("fr11", "count(o.id)", _repeated("JOIN r and JOIN o", _group("customers"))),
    ("fr12", "min(b2.id)", _repeated("JOIN b2", _group("cust"))),
    ("fr13", "min(b2.id)", _repeated("JOIN b2", _group("cust"))),
    ("fr14", "min(b2.id)", _repeated("JOIN b2", _group("cust"))),
    # A nullable key protects no group.
    ("fr15", "count(customers.id)", _repeated("JOIN o", _group("o"))),
    # A composite key covered only in part.
    (
        "fr16",
        "count(ships.id)",
        _repeated(
            "JOIN l",
            "declare a unique key on lines.ord_id (matched by JOIN l), or "
            + _group("l"),
        ),
    ),
    ("fr17", "count(c.id)", _repeated("JOIN c", _group("orders_x"))),
    ("fr18", "min(b2.id)", _repeated("JOIN b2", _group("cust"))),
    ("chain_refused", "max(r.id)", _repeated("JOIN r", _group("orders"))),
    # The argument reads r through two `let:` names, and the group key is a
    # renamed field that is no key.
    ("let_argument", "count(shown)", _repeated("JOIN r", _group("orders"))),
    ("renamed_non_key", "count(o.id)", _repeated("JOIN o", _group("customers"))),
    # One key serves two JOINs; a composite key; two keys; two group keys.
    (
        "one_key_two_joins",
        "count(c.name)",
        _repeated(
            "JOIN c",
            "declare a unique key on orders.customer_id (matched by JOINs c and d), "
            "or " + _group("orders"),
        ),
    ),
    (
        "composite_key_text",
        "count(lines.ord_id)",
        _repeated(
            "JOIN s",
            "declare a unique key on ships (ord_id, line_no) (matched by JOIN s), or "
            + _group("s"),
        ),
    ),
    (
        "two_keys",
        "count(r.label)",
        _repeated(
            "JOIN r",
            "declare a unique key on orders.customer_id (matched by JOIN c) and a "
            "unique key on customers.region_id (matched by JOIN r), or "
            + _group("orders"),
        ),
    ),
    (
        "unique_keys_of_two",
        "count(orders.id)",
        _repeated(
            "JOIN r and JOIN k",
            "group by unique keys of r and k whose fields are all not null",
        ),
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

    message = _repeated("JOIN r", _group("orders"))
    assert located(fanout.fanout("not_exempt")) == [
        ("PIE-S2381", message, *_at("not_exempt", call))
        for call in ("min(r.id)", "max(r.id)", "count_distinct(r.label)", "count(r.id)")
    ]


def test_an_aggregate_that_reads_no_input_names_no_repeated_join() -> None:
    """Its rows are repeated by every JOIN at once (single files also refuse
    the argument with PIE-S2315)."""

    source = (
        _FANOUT_SOURCE.split("query named_customers:")[0]
        + "query no_field:\n    from orders\n    cross join regions as r: from orders\n"
        "    select:\n        n = sum(1)\n"
    )
    facts = join_script(source)
    lines = source.split("\n")
    line = lines.index("        n = sum(1)") + 1
    assert located(facts.fanout("no_field")) == [
        (
            "PIE-S2381",
            "An aggregate may read rows that a JOIN repeats; group by unique keys of "
            "orders and r whose fields are all not null",
            line,
            13,
        )
    ]


# Where both modes refuse an aggregate for fan-out, the single-file message is
# the project's cause clause with its first letter capitalized; the project
# accepts the refusals in which single files are stricter.
_SAME_CLAUSE = (
    "fr1",
    "fr2",
    "fr3",
    "fr6",
    "fr7",
    "fr8",
    "fr9",
    "fr10",
    "fr11",
    "fr15",
    "fr16",
    "not_exempt",
    "chain_refused",
    "let_argument",
    "renamed_non_key",
    "one_key_two_joins",
    "composite_key_text",
    "two_keys",
    "unique_keys_of_two",
)
# The project proves reverse M4/RIGHT self relationships; the bounded
# single-file rule deliberately gives those directions no edge.
_STRICTER = ("fr5", "fr12", "fr13", "fr14", "fr17", "fr18")


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
    assert tuple(clauses) == (*_SAME_CLAUSE[:3], "fr4", *_SAME_CLAUSE[3:])
    for query in _SAME_CLAUSE:
        messages = {item.message for item in fanout.fanout(query)}
        assert messages == {clauses[query][0].upper() + clauses[query][1:]}
    # The project carries a key through the query `named_customers`.
    assert clauses["fr4"] == (
        "an aggregate may read rows repeated by JOIN c; " + _group("c")
    )
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
    cross join customers as peer: from customers
    let:
        first_key = {protected}.id
        group_key = first_key
        first_value = {protected}.id
        repeated_value = first_value
    group by: group_key
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
        ("PIE-S2381", _repeated("JOIN peer", _group(other)), line, 20)
    ]


@pytest.mark.parametrize("grouped", ("r", "c"))
def test_refined_left_subtree_cannot_determine_an_earlier_cross_input(
    grouped: str,
) -> None:
    source = (
        _FANOUT_SOURCE.split("query named_customers:")[0]
        + f"""query refined:
    from orders
    cross join regions as r: from orders
    left join customers as c:
        from orders
        via order_customer
        on r.id == c.region_id
    inner join orders_x as x:
        from c
        via ox_customer
    group by: {grouped}.id
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
                _repeated("JOIN r", _group("r")),
                source.splitlines().index("        n = count(orders.id)") + 1,
                13,
            )
        ]
    )
    assert located(result.diagnostics) == expected
