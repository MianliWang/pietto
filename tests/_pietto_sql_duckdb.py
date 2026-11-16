"""A DuckDB project and its contract (docs/spec/duckdb-arrow-route-v1.md):
one `duckdb.arrow("orders")` source of the four admitted field types, and a
contract that admits every admitted statement over it."""

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
                "representation": copy.deepcopy(REPRESENTATIONS[kind])
                | {"nullable": nullable},
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
