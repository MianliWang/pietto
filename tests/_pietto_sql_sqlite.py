"""A SQLite project and its contract (docs/spec/sqlite-project-v1.md): one
`sqlite.table("orders")` source of the four admitted field types, and a
contract that admits every tier 1 statement over it."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

REPRESENTATIONS = {
    "Int": {
        "storage": {"kind": "sqlite_integer"},
        "domain": {"kind": "int_range", "min": str(-(2**63)), "max": str(2**63 - 1)},
    },
    "Text": {
        "storage": {"kind": "sqlite_text"},
        "domain": {
            "kind": "text",
            "max_characters": 100,
            "encoding": "UTF-8",
            "collation": "BINARY",
            "padding": "NO PAD",
        },
    },
    "Bool": {"storage": {"kind": "sqlite_bool01"}, "domain": {"kind": "bool01"}},
    "Float": {
        "storage": {"kind": "sqlite_real"},
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

source orders: Order = sqlite.table("orders")
"""
PROJECTION = """table result:
    from orders
    select:
        id
        note
"""
PROJECTION_SQL = (
    "SELECT `s0`.`id` AS `id`, `s0`.`note` AS `note` FROM `main`.`orders` AS `s0`"
)


def statement(name: str, value: object) -> dict[str, object]:
    return {"key": name, "scope": "statement", "value": value}


def source_entry(
    name: str = "orders", fields: tuple[tuple[str, str, bool], ...] = FIELDS
) -> dict[str, Any]:
    return {
        "selector": {"module": "main.pietto", "kind": "source", "name": name},
        "relation": {"namespace": "main", "name": name},
        "scan": "relation_rows",
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
        "target": {"family": "sqlite", "release": "3.53.1"},
        "sources": list(sources) or [source_entry()],
        "environment": [
            statement("client_encoding", "UTF-8"),
            statement("operator_environment", "builtin_only"),
            statement("parameter_protocol", "sqlite_prepared"),
        ],
    }


def write(
    root: Path, body: str, document: dict[str, Any], header: str = HEADER
) -> Path:
    """The project's files as bytes, so their digests hold on every platform."""
    root.mkdir(parents=True)
    (root / "pietto.toml").write_bytes(
        b'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_bytes((header + "\n" + body).encode("utf-8"))
    (root / "contract.json").write_bytes(json.dumps(document).encode("utf-8"))
    return root
