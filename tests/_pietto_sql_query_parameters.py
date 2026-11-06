"""The published one-source emission fixture with a header-parameter query."""

from __future__ import annotations

import json
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
    contract = json.loads(
        probe.fixture(target, "T_row_direct", "table_preserve")["contract"]
    )
    pg = target == "postgres"
    physical = {
        "Int": (
            {"kind": "pg_int4" if pg else "my_int"},
            {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
        ),
        "Timestamp": (
            {"kind": "pg_timestamp" if pg else "my_datetime", "fractional_seconds": 6},
            {"kind": "timestamp"},
        ),
        "Date": ({"kind": "pg_date" if pg else "my_date"}, {"kind": "date"}),
        "UUID": (
            {"kind": "pg_uuid" if pg else "my_uuid_bytes"},
            {"kind": "uuid", "encoding": "standard_bytes"},
        ),
        "Decimal(9, 2)": (
            {"kind": "pg_numeric" if pg else "my_decimal", "precision": 9, "scale": 2},
            {"kind": "decimal", "precision": 9, "scale": 2},
        ),
    }
    contract["sources"][0]["fields"] = [
        {
            "ordinal": i,
            "name": name,
            "column": name,
            "representation": {
                "storage": physical[kind][0],
                "nullable": nullable,
                "domain": physical[kind][1],
            },
        }
        for i, (name, kind, nullable) in enumerate(TYPED_FIELDS)
    ]
    contract["environment"] += [
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact" if pg else "lower_case_table_names=0",
        },
        {"key": "parameter_protocol", "scope": "statement", "value": PROTOCOL[target]},
    ]
    source = (
        "shape Row:\n"
        + "".join(
            f"    {name}: {kind}{' | None' if nullable else ''}\n"
            for name, kind, nullable in TYPED_FIELDS
        )
        + f'source rows: Row = {target}.table("opaque.locator.not.sql")\n'
        + body
    )
    return probe.build_case(
        root / target, source, probe.encoded(contract).decode(), "preserve_literals"
    )
