"""A DuckDB project and its contract (docs/spec/duckdb-arrow-route-v1.md):
one `duckdb.arrow("orders")` source of the four tier 1 field types, or of
`Date`, `Timestamp` and `Decimal` fields (TYPED_HEADER), and a contract that
admits every admitted statement over it."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

INT = {
    "storage": {"kind": "arrow_int64"},
    "domain": {"kind": "int_range", "min": str(-(2**63)), "max": str(2**63 - 1)},
}
REPRESENTATIONS = {
    "Int": INT,
    "Text": {
        "storage": {"kind": "arrow_string"},
        "domain": {
            "kind": "text",
            "max_characters": 100,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    },
    "Bool": {"storage": {"kind": "arrow_bool"}, "domain": {"kind": "bool01"}},
    "Float": {
        "storage": {"kind": "arrow_float64"},
        "domain": {"kind": "finite_float", "format": "binary64"},
    },
    "Date": {"storage": {"kind": "arrow_date32"}, "domain": {"kind": "date"}},
    "Timestamp": {
        "storage": {"kind": "arrow_timestamp_us"},
        "domain": {"kind": "timestamp"},
    },
}
FIELDS = (
    ("id", "Int", False),
    ("amount", "Int", False),
    ("note", "Text", True),
    ("ok", "Bool", False),
    ("price", "Float", False),
)
HEADER = """shape Order:
    id: Int
    amount: Int
    note: Text | None
    ok: Bool
    price: Float

source orders: Order = duckdb.arrow("orders")
"""
PROJECTION = """table result:
    from orders
    select:
        id
        note
"""
PROJECTION_SQL = 'SELECT "c0" AS "id", "c2" AS "note" FROM temp.main."pietto_arrow_0"'
# Two keys, one nullable, each aggregate and a having on a label that is also
# a capture column's name.
GROUPED = """query result(min_total: Int):
    from orders
    group by note, ok
    select:
        note
        ok
        n = count()
        filled = count(note)
        c1 = sum(amount)
        low = min(price)
        high = max(id)
    having c1 >= min_total
"""
GROUPED_SQL = (
    'SELECT "c2" AS "note", "c3" AS "ok", count(*) AS "n", count("c2") AS "filled",'
    ' CAST(sum("c1") AS BIGINT) AS "c1", min("c4") AS "low", max("c0") AS "high"'
    ' FROM temp.main."pietto_arrow_0"'
    ' GROUP BY "pietto_arrow_0"."c2", "pietto_arrow_0"."c3"'
    ' HAVING CAST(sum("pietto_arrow_0"."c1") AS BIGINT) >= CAST($1 AS BIGINT)'
)

# GROUPED ordered by two aggregates and a key, each restated, then limited.
ORDERED = (
    GROUPED + "    order by:\n        c1 desc\n        low\n        note\n    limit 4\n"
)
ORDERED_SQL = GROUPED_SQL + (
    ' ORDER BY CAST(sum("pietto_arrow_0"."c1") AS BIGINT) DESC NULLS FIRST,'
    ' min("pietto_arrow_0"."c4") ASC NULLS LAST, "pietto_arrow_0"."c2" ASC NULLS LAST'
    " LIMIT 4"
)
# Parameters of the four types, first read in another order than declared and
# one read twice, beside a signed literal, a null test and and, or and not.
PREDICATED = (
    "query result(label: Text, low: Int, flag: Bool, cap: Float):\n"
    "    from orders\n"
    "    where (low <= amount and not (note == label)) or (ok == flag and price"
    " < cap) or (amount != low and note is None and id > -3)\n"
    "    select:\n        id\n        note\n"
)
PREDICATED_SQL = (
    'SELECT "c0" AS "id", "c2" AS "note" FROM temp.main."pietto_arrow_0" WHERE'
    ' ((CAST($1 AS BIGINT) <= "c1" AND (NOT "c2" = CAST($2 AS VARCHAR)))'
    ' OR ("c3" = CAST($3 AS BOOLEAN) AND "c4" < CAST($4 AS DOUBLE)))'
    ' OR (("c1" <> CAST($1 AS BIGINT) AND "c2" IS NULL)'
    ' AND "c0" > CAST(-3 AS BIGINT))'
)


# The tier 2 types: one field of each, two Decimals of other scales.
TYPED_FIELDS = (
    ("id", "Int", False),
    ("day", "Date", True),
    ("at", "Timestamp", False),
    ("cost", "Decimal(12, 2)", True),
    ("big", "Decimal(38, 10)", False),
)
TYPED_HEADER = """shape Event:
    id: Int
    day: Date | None
    at: Timestamp
    cost: Decimal(12, 2) | None
    big: Decimal(38, 10)

source orders: Event = duckdb.arrow("orders")
"""


def representation(kind: str) -> dict[str, Any]:
    """The route's representation of a field type; a `Decimal(p, s)` has its
    precision and scale in its storage and its domain."""
    if kind.startswith("Decimal("):
        precision, scale = (int(k) for k in kind[8:-1].split(","))
        pair = {"precision": precision, "scale": scale}
        return {
            "storage": {"kind": "arrow_decimal128"} | pair,
            "domain": {"kind": "decimal"} | pair,
        }
    return copy.deepcopy(REPRESENTATIONS[kind])


def filtered(operator: str, parameter: str = "min_amount: Int") -> str:
    return f"""query result({parameter}):
    from orders
    where amount {operator} min_amount
    select:
        id
        price
"""


def statement(name: str, value: object) -> dict[str, object]:
    return {"key": name, "scope": "statement", "value": value}


def source_entry(
    name: str = "orders", fields: tuple[tuple[str, str, bool], ...] = FIELDS
) -> dict[str, Any]:
    return {
        "selector": {"module": "main.pietto", "kind": "source", "name": name},
        "relation": {"namespace": "arrow", "name": name},
        "scan": "arrow_registration",
        "fields": [
            {
                "ordinal": i,
                "name": field,
                "column": field,
                "representation": representation(kind) | {"nullable": nullable},
            }
            for i, (field, kind, nullable) in enumerate(fields)
        ],
        "premises": [
            {"key": key, "scope": "source", "value": True}
            for key in ("row_domain_matches", "read_only_object")
        ],
    }


def contract(*sources: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "pietto.emission-contract.v1",
        "target": {"family": "duckdb", "release": "2.0.0"},
        "sources": list(sources) or [source_entry()],
        "environment": [
            statement("client_encoding", "UTF8"),
            statement("operator_environment", "builtin_only"),
            statement("parameter_protocol", "duckdb_prepared"),
        ],
    }


def write(
    root: Path, body: str, document: dict[str, Any], header: str = HEADER
) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(header + "\n" + body, encoding="utf-8")
    (root / "contract.json").write_text(json.dumps(document), encoding="utf-8")
    return root
