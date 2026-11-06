"""Table and query rows passed to a relationship, matched by field name.

`CANONICAL` is the style example and `HEAD + GROUPED` its grouped variant;
`written_on` spells either's calls as their bodies. `ROWS` maps each variant
to a source and the diagnostics a single file reports for it, as (code,
message, line, column).
"""

from __future__ import annotations

CANONICAL = """shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    region_id: Int

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id

query active_customers:
    from customers
    where customers.region_id > 0
    select id, region_id

query result:
    from orders
    let buyer = active_customers
    left join buyer on order_customer(orders, buyer)
    select order_id = orders.id, region_id = buyer.region_id
"""

# A grouped query offers its GROUP BY key as a unique key (B14), so counting
# the customers of each region over a LEFT JOIN on it repeats no row.
GROUPED = """shape Spend:
    customer_id: Int
    orders_n: Int
    spend_key = unique(customer_id)

relationship customer_spend(customer: Customer, spend: Spend): customer.id == spend.customer_id

query spend:
    from orders
    group by customer_id
    select customer_id, orders_n = count()

query result:
    from customers
    let s = spend
    left join s on customer_spend(customers, s)
    group by customers.region_id
    select region_id = customers.region_id, customers_n = count(customers.id)
"""

HEAD = CANONICAL.split("query result:", 1)[0]
_UNAVAILABLE = (
    "Unavailable row argument for relationship order_customer parameter customer"
)
type Located = list[tuple[str, str, int, int]]


def written_on(source: str) -> str:
    """``source`` with each relationship call written as its body."""

    return source.replace(
        "order_customer(orders, buyer)", "orders.customer_id == buyer.id"
    ).replace("customer_spend(customers, s)", "customers.id == s.customer_id")


def _reader(rows: str, line: int, reason: str) -> tuple[str, Located]:
    """``rows`` (relation ``c``) passed to order_customer in a `result` JOIN,
    refused for ``reason`` at its argument on ``line``."""

    return (
        HEAD
        + rows
        + "\nquery result:\n    from orders\n    let buyer = c\n"
        + "    inner join buyer on order_customer(orders, buyer)\n"
        + "    select order_id = orders.id\n",
        [("PIE-S2604", f"{_UNAVAILABLE}: {reason}", line, 48)],
    )


ROWS: dict[str, tuple[str, Located]] = {
    "query": (CANONICAL, []),
    "table": (
        CANONICAL.replace("query active_customers:", "table active_customers:"),
        [],
    ),
    "grouped": (HEAD + GROUPED, []),
    # A FROM row of a query without JOIN, through a type alias field.
    "from_alias": (
        "type RegionId = Int\n\n"
        "shape Regional:\n    region_id: RegionId\n\n"
        "relationship in_region(row: Regional): row.region_id > 1\n\n"
        + HEAD
        + "query result:\n    from active_customers\n"
        "    where in_region(active_customers)\n"
        "    select id = active_customers.id\n",
        [],
    ),
    "any": (
        HEAD + "query result:\n    from orders\n"
        "    where any(order_customer(orders, c) for c in active_customers)\n"
        "    select order_id = orders.id\n",
        [],
    ),
    # Arithmetic keeps an unknown nullability, which fits no field without
    # `| None`, as for a def parameter (PIE-S2395).
    "computed": _reader(
        "query c:\n    from customers\n"
        "    select id, region_id = customers.region_id + 1\n",
        27,
        "column region_id is Int of unknown nullability, field region_id is Int",
    ),
    "missing": _reader(
        "query c:\n    from customers\n    select id\n", 27, "no column region_id"
    ),
    "mistyped": _reader(
        'query c:\n    from customers\n    select id, region_id = "r"\n',
        27,
        "column region_id is Text, field region_id is Int",
    ),
    "nullable": _reader(
        "shape Lead:\n    id: Int\n    region_id: Int | None\n\n"
        'source leads: Lead = postgres.table("shop.leads")\n\n'
        "query c:\n    from leads\n    select id, region_id\n",
        33,
        "column region_id is Int | None, field region_id is Int",
    ),
    "enum": (
        "enum Tier:\n    gold\n    silver\n\n"
        "enum Level:\n    gold\n    silver\n\n"
        "shape Ranked:\n    id: Int\n    tier: Tier\n\n"
        "shape Member:\n    id: Int\n    tier: Tier\n    level: Level\n\n"
        'source members: Member = postgres.table("shop.members")\n\n'
        "relationship same_member(a: Ranked, b: Ranked): a.id == b.id\n\n"
        "query tiers:\n    from members\n    select id, tier\n\n"
        "query levels:\n    from members\n    select id, tier = members.level\n\n"
        "query result:\n    from tiers\n    let l = levels\n"
        "    inner join l on same_member(tiers, l)\n"
        "    select id = tiers.id\n",
        [
            (
                "PIE-S2604",
                "Unavailable row argument for relationship same_member parameter b: "
                "column tier is Level, field tier is Tier",
                33,
                40,
            )
        ],
    ),
    # Field names never stand in for a source's shape identity.
    "other_shape": (
        "shape Person:\n    id: Int\n    region_id: Int\n\n"
        'source people: Person = postgres.table("shop.people")\n\n'
        + HEAD
        + "query result:\n    from orders\n    let buyer = people\n"
        "    inner join buyer on order_customer(orders, buyer)\n"
        "    select order_id = orders.id\n",
        [
            (
                "PIE-S2604",
                "Relationship order_customer parameter customer requires declared "
                "shape Customer; the actual row has a different shape identity",
                29,
                48,
            )
        ],
    ),
    # The parameter shape's `unique` is no key of a query's rows.
    "shape_unique": (
        HEAD
        + GROUPED.replace(
            "    group by customer_id\n    select customer_id, orders_n = count()\n",
            "    select customer_id, orders_n = orders.id\n",
        ),
        [
            (
                "PIE-S2381",
                "An aggregate may read rows repeated by JOIN s; two-level "
                "route: group a first query by a unique key of each input the "
                "aggregate reads and by every other field that query selects, "
                "select an aggregate such as `count()` in it too, then "
                "aggregate in a second query that reads `from` it",
                36,
                59,
            )
        ],
    ),
}

# `CANONICAL` with the customers and their query imported from rows.pietto.
IMPORTED = {
    "rows.pietto": """shape Customer:
    id: Int
    region_id: Int

source customers: Customer = postgres.table("shop.customers")

query active_customers:
    from customers
    where customers.region_id > 0
    select id, region_id

export (
    shape Customer,
    query active_customers,
)
""",
    "main.pietto": """from "rows.pietto" import (
    shape Customer,
    query active_customers,
)

shape Order:
    id: Int
    customer_id: Int

source orders: Order = postgres.table("shop.orders")

relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id

query result:"""
    + CANONICAL.split("query result:", 1)[1],
}

# Module rows across modules: a local query over an imported source and an
# imported query bind; an enum of another module with the same name does not.
MODULES: dict[str, tuple[dict[str, str], Located]] = {
    "imported": (IMPORTED, []),
    "enum": (
        {
            "types.pietto": "enum Tier:\n    gold\n    silver\n\n"
            "shape Ranked:\n    id: Int\n    tier: Tier\n\n"
            "shape Member:\n    id: Int\n    tier: Tier\n\n"
            'source members: Member = postgres.table("shop.members")\n\n'
            "query tiers:\n    from members\n    select id, tier\n\n"
            "export (\n    shape Ranked,\n    source members,\n    query tiers,\n)\n",
            "other.pietto": "enum Tier:\n    gold\n    silver\n\n"
            "shape Guest:\n    id: Int\n    tier: Tier\n\n"
            'source guests: Guest = postgres.table("shop.guests")\n\n'
            "export (\n    source guests,\n)\n",
            "main.pietto": 'from "types.pietto" import (\n    shape Ranked,\n'
            "    source members,\n    query tiers,\n)\n"
            'from "other.pietto" import (\n    source guests,\n)\n\n'
            "relationship gold(a: Ranked): a.id > 0\n\n"
            "query local:\n    from members\n    select id, tier\n\n"
            "query r1:\n    from local\n    where gold(local)\n    select id = local.id\n\n"
            "query r2:\n    from tiers\n    where gold(tiers)\n    select id = tiers.id\n\n"
            "query other:\n    from guests\n    select id, tier\n\n"
            "query r3:\n    from other\n    where gold(other)\n    select id = other.id\n",
        },
        [
            (
                "PIE-S2604",
                "Unavailable row argument for relationship gold parameter a: "
                'column tier is Tier from "other.pietto", '
                'field tier is Tier from "types.pietto"',
                32,
                16,
            )
        ],
    ),
}


def project_contract(target: str = "postgres", customers: str = "main.pietto") -> str:
    """The emission contract of `CANONICAL`'s two sources, in schema ``shop``,
    with ``customers`` declared in that module."""

    import json

    pg = target == "postgres"
    fields = {"orders": ("id", "customer_id"), "customers": ("id", "region_id")}
    representation = {
        "storage": {"kind": "pg_int8" if pg else "my_bigint"},
        "nullable": False,
        "domain": {"kind": "int_range", "min": "0", "max": "10000000"},
    }
    environment = {
        "client_encoding": "UTF8" if pg else "utf8mb4",
        "operator_environment": "builtin_only",
        "identifier_case": "quoted_exact" if pg else "lower_case_table_names=0",
    }
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": target, "release": "18.6" if pg else "8.4.12"},
            "sources": [
                {
                    "selector": {
                        "module": customers if n == "customers" else "main.pietto",
                        "kind": "source",
                        "name": n,
                    },
                    "relation": {"namespace": "shop", "name": n},
                    "scan": "relation_rows",
                    "fields": [
                        {
                            "ordinal": i,
                            "name": f,
                            "column": f,
                            "representation": representation,
                        }
                        for i, f in enumerate(names)
                    ],
                    "premises": [
                        {"key": "row_domain_matches", "scope": "source", "value": True},
                        {"key": "read_only_object", "scope": "source", "value": True},
                    ],
                }
                for n, names in fields.items()
            ],
            "environment": [
                {"key": key, "scope": "statement", "value": value}
                for key, value in environment.items()
            ],
        }
    )
