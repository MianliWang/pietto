"""The published one-source emission fixture with a header-parameter query."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import _pietto_sql_emission as probe

PROTOCOL = {"postgres": "postgres_extended", "mysql": "mysql_prepared"}


def parameterized_case(
    root: Path,
    target: str,
    body: str,
    policy: str = "preserve_literals",
    *,
    protocol: bool = True,
    limits: dict[str, int] | None = None,
) -> Any:
    """Build the fixture with ``body`` as its selected query ``result``.

    The contract adds exact identifier case, ``limits`` as its resource limits
    and, unless ``protocol`` is false, the native parameter protocol every
    parameter read requires.
    """
    item = probe.parameterized_fixture(
        target, body, policy, protocol=protocol, limits=limits
    )
    return probe.build_case(
        root / target / policy, item["source"], item["contract"], policy
    )


# One source of each Decimal/Date/Timestamp/UUID carrier beside an int4 id:
# (name, Pietto type, nullable), the carriers of a typed header parameter.
TYPED_FIELDS = (
    ("id", "Int", False),
    ("ts", "Timestamp", False),
    ("d", "Date", False),
    ("d2", "Date", True),
    ("u", "UUID", False),
    ("money", "Decimal(9, 2)", False),
)
# Q4: one read of each typed parameter, all in WHERE.
TYPED_BODY = """query result(since: Timestamp, day: Date | None, key: UUID, floor: Decimal(9, 2)):
    from rows
    where ts >= since and d2 == day and u == key and money >= floor
    select:
        id
"""


def typed_case(root: Path, target: str, body: str = TYPED_BODY) -> Any:
    """Build ``body`` over ``TYPED_FIELDS`` with the exact source carriers, the
    identifier-case premise and the native parameter protocol."""
    entry, _, block = body.partition("\n")
    return probe.temporal_case(
        root / target,
        target,
        block,
        fields=TYPED_FIELDS,
        entry=entry,
        environment=(
            {
                "key": "identifier_case",
                "scope": "statement",
                "value": "quoted_exact"
                if target == "postgres"
                else "lower_case_table_names=0",
            },
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": PROTOCOL[target],
            },
        ),
    )


# S09: MySQL typed header-parameter bodies over TYPED_FIELDS. Each body of
# MYSQL_TYPED_OPEN reads every typed parameter it declares only in a cell (a
# whole SELECT item, or the right operand of a comparison with a source field
# of its type that the WHERE reaches through `and` and `or`); each body of
# MYSQL_TYPED_REFUSED leaves at least one read, or the query, outside them,
# or declares a UUID, which has no MySQL carrier (S09 withdrew it, D77.07).
_HEADER = "query result(day: Date, since: Timestamp, floor: Decimal(9, 2)):"
_ITEMS = "    select:\n        id\n        a = since\n        c = floor\n"
MYSQL_TYPED_OPEN = {
    "where": "query result(since: Timestamp, day: Date | None, floor: Decimal(9, 2)):\n"
    "    from rows\n    where ts >= since and d2 == day and money >= floor\n"
    "    select:\n        id\n",
    "select": f"{_HEADER}\n    from rows\n    select:\n        id\n"
    "        a = day\n        b = since\n        e = floor\n",
    "twice": "query result(day: Date):\n    from rows\n"
    "    where d == day or d == day\n    select:\n        id\n",
    "mixed": "query result(low: Int, day: Date | None, floor: Decimal(9, 2)):\n"
    "    from rows\n    where id > low and (d2 < day or money != floor)\n"
    "    select:\n        id\n        e = floor\n        f = day\n",
    "parenthesized": f"{_HEADER}\n    from rows\n    where (d <= day)\n"
    "    select:\n        id\n        a = (since)\n        c = floor\n",
}
MYSQL_TYPED_REFUSED = {
    "left_operand": f"{_HEADER}\n    from rows\n"
    "    where day == d and ts >= since and money >= floor\n"
    "    select:\n        id\n",
    "not": f"{_HEADER}\n    from rows\n    where not (d == day)\n{_ITEMS}",
    "between": f"{_HEADER}\n    from rows\n    where day <= d <= day\n{_ITEMS}",
    "in_list": f"{_HEADER}\n    from rows\n    where d in (day, day)\n{_ITEMS}",
    "is_none": f"{_HEADER}\n    from rows\n    where day is None\n{_ITEMS}",
    "call": f"{_HEADER}\n    from rows\n    where date_of(ts) == day\n{_ITEMS}",
    "coalesce": f"{_HEADER}\n    from rows\n    select:\n        id\n"
    "        a = coalesce(day, d)\n        b = since\n        e = floor\n",
    "let": f"{_HEADER}\n    from rows\n    let x = d\n    where x == day\n{_ITEMS}",
    "parameter_pair": "query result(day: Date, other: Date):\n    from rows\n"
    "    where d == day and day == other\n    select:\n        id\n",
    "unread": "query result(low: Int, day: Date | None):\n    from rows\n"
    "    where id > low\n    select:\n        id\n",
    "order": f"{_HEADER}\n    from rows\n    where d == day\n{_ITEMS}    order by id\n",
    "limit": f"{_HEADER}\n    from rows\n    where d == day\n{_ITEMS}    limit 3\n",
    "group": "query result(day: Date):\n    from rows\n    where d == day\n"
    "    group by:\n        d\n    select:\n        d\n        n = count()\n",
    "window": f"{_HEADER}\n    from rows\n    where d == day\n    select:\n"
    "        id\n        r = row_number() window(order by id)\n"
    "        a = since\n        c = floor\n",
    "upstream": "query up:\n    from rows\n    select:\n        id\n        d\n"
    "query result(day: Date):\n    from up\n    where d == day\n"
    "    select:\n        id\n",
    # In their cells, but another rule refuses the query (D77.37).
    "add_months": f"{_HEADER}\n    from rows\n    where d == day\n    select:\n"
    "        id\n        m = add_months(d, 1)\n        a = since\n        c = floor\n",
    "decimal_conflict": "query result(floor: Decimal(10, 2)):\n    from rows\n"
    "    where money >= floor\n    select:\n        id\n",
    "decimal_arithmetic": "query result(floor: Decimal(9, 2)):\n    from rows\n"
    "    where money >= floor\n    select:\n        id\n        t = money + id\n",
    # Each former UUID cell, alone or beside the other types' cells (D77.37).
    "uuid_where": "query result(key: UUID):\n    from rows\n    where u == key\n"
    "    select:\n        id\n",
    "uuid_twice": "query result(key: UUID):\n    from rows\n"
    "    where u == key or u == key\n    select:\n        id\n",
    "uuid_select": "query result(key: UUID):\n    from rows\n    select:\n"
    "        id\n        c = key\n",
    "uuid_where_beside_cells": TYPED_BODY,
    "uuid_select_beside_cells": "query result(day: Date, since: Timestamp, key: UUID, "
    "floor: Decimal(9, 2)):\n    from rows\n    select:\n        id\n"
    "        a = day\n        b = since\n        c = key\n        e = floor\n",
}
