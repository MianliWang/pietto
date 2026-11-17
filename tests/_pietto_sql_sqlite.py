"""A SQLite project and its contract (docs/spec/sqlite-project-v1.md): one
`sqlite.table("orders")` source of the four admitted field types, and a
contract that admits every tier 1 statement over it. Beside them, the SQLite
class of the native tests (docs/development.md, "SQLite target validation")
and the judge of the `sqlite_file` route's results."""

from __future__ import annotations

import copy
import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from pietto.sql.sqlite import QUALIFIED_SQLITE_BUILD, SQLiteBuild

SQLITE_CLASS_VARIABLE = "PIETTO_SQLITE_CLASS"
SQLITE_CLASSES = ("hosted-refusal", "qualified", "report")


def observe(connection: sqlite3.Connection) -> SQLiteBuild:
    release, source_id = connection.execute(
        "SELECT sqlite_version(), sqlite_source_id()"
    ).fetchone()
    options = connection.execute("PRAGMA compile_options").fetchall()
    return SQLiteBuild(release, source_id, tuple(row[0] for row in options))


def refusal(observed: SQLiteBuild) -> str | None:
    """The first part of the identity that differs, or None when it is the
    measured build."""

    if observed.release != QUALIFIED_SQLITE_BUILD.release:
        return "SQLITE_BUILD_RELEASE"
    if observed.source_id != QUALIFIED_SQLITE_BUILD.source_id:
        return "SQLITE_BUILD_SOURCE"
    if observed.compile_options != QUALIFIED_SQLITE_BUILD.compile_options:
        return "SQLITE_BUILD_OPTIONS"
    return None


def sqlite_class(environ: Mapping[str, str], option: str | None) -> str:
    """The declared class; with none, hosted CI keeps the refusal and any
    other run reports. A class never qualifies a build."""

    declared = environ.get(SQLITE_CLASS_VARIABLE)
    if option is not None and declared is not None and declared != option:
        raise ValueError("PIETTO_SQLITE_CLASS_CONFLICT")
    value = option if option is not None else declared
    if value is None:
        return "hosted-refusal" if environ.get("GITHUB_ACTIONS") == "true" else "report"
    if value not in SQLITE_CLASSES:
        raise ValueError("PIETTO_SQLITE_CLASS_UNKNOWN")
    return value


def decide(category: str | None, declared: str) -> bool:
    """True when nothing differs; otherwise `hosted-refusal` keeps the
    asserted refusal (False), `qualified` fails and `report` skips with a
    counted line."""

    if category is None:
        return True
    if declared == "hosted-refusal":
        return False
    if declared == "qualified":
        pytest.fail(f"PIETTO_SQLITE_REQUIRED {category}", pytrace=False)
    pytest.skip(f"PIETTO_NOT_RUN sqlite-native {category}")


def qualified(observed: SQLiteBuild, declared: str) -> bool:
    return decide(refusal(observed), declared)


def result_facts(table: Any) -> tuple[list[tuple[str, str, bool]], list[Any]]:
    """What the judge reads of a PyArrow table: each column's name, type and
    nullability, and the rows as Python values."""
    return [(f.name, str(f.type), f.nullable) for f in table.schema], table.to_pylist()


def _typed(value: object) -> tuple[str, str]:
    # `True == 1`, `1.0 == 1` and `-0.0 == 0.0` in Python; a type and a repr
    # tell each pair apart.
    return type(value).__name__, repr(value)


def judge(
    columns: object,
    records: object,
    expected_columns: Sequence[tuple[str, str, bool]],
    expected_rows: Sequence[tuple[object, ...]],
    *,
    ordered: bool = True,
) -> None:
    """The `sqlite_file` route's result judge (lesson 72-4): the columns
    are exactly the expected names, Arrow types and nullability, and the
    records hold the expected rows value for value, each of the same Python
    type and zero sign, in order or, unordered, as a bag. It reads only what
    it is given and raises AssertionError at the first difference."""
    assert type(columns) is list and columns == list(expected_columns), columns
    labels = [name for name, _type, _nullable in expected_columns]
    assert type(records) is list, records
    assert all(type(r) is dict and list(r) == labels for r in records), records
    seen = [tuple(_typed(v) for v in r.values()) for r in records]
    wanted = [tuple(_typed(v) for v in row) for row in expected_rows]
    if not ordered:
        seen, wanted = sorted(seen), sorted(wanted)
    assert seen == wanted, (seen, wanted)


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


# A second source for JOINs (S13a), keyed by its `id`.
CUSTOMER_FIELDS = (
    ("id", "Int", False),
    ("name", "Text", False),
    ("vip", "Bool", True),
    ("rate", "Float", False),
)
JOINED_HEADER = (
    HEADER
    + """
shape Customer:
    id: Int
    name: Text
    vip: Bool | None
    rate: Float
    customer_key = unique(id)

source customers: Customer = sqlite.table("customers")
"""
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


def joined_contract(*, customers: bool = True) -> dict[str, Any]:
    """The contract of both sources, or of `orders` alone."""
    entries = [source_entry()]
    if customers:
        entries.append(source_entry("customers", CUSTOMER_FIELDS))
    return contract(*entries)


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
