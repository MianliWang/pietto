"""SQLite project emission (docs/spec/sqlite-project-v1.md).

A project `sqlite.table` source checks, and the PostgreSQL, MySQL and DuckDB
emitters refuse it with the blockers they give a source of another family.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _pietto_sql_duckdb import FIELDS, HEADER, PROJECTION, contract, source_entry, write
from pietto.compiler import compile_sql

# Each target's release, its storage kind of each logical type (DuckDB keeps
# the helper's), and a source of another family that it already refuses.
TARGETS = {
    "postgres": (
        "18.6",
        {"Int": "pg_int8", "Text": "pg_text", "Bool": "pg_bool", "Float": "pg_float8"},
        "duckdb.arrow",
    ),
    "mysql": (
        "8.4.12",
        {
            "Int": "my_bigint",
            "Text": "my_varchar",
            "Bool": "my_bool01",
            "Float": "my_double",
        },
        "duckdb.arrow",
    ),
    "duckdb": ("2.0.0", None, "postgres.table"),
}


@pytest.mark.parametrize("dialect", TARGETS)
def test_other_targets_refuse_a_sqlite_source_as_another_family(
    tmp_path: Path, dialect: str
) -> None:
    release, storage, control = TARGETS[dialect]
    entry = source_entry()
    if storage is not None:
        entry["scan"] = "relation_rows"
        entry["relation"] = {"namespace": "public", "name": "orders"}
        for field, (_, logical, _) in zip(entry["fields"], FIELDS, strict=True):
            kind = storage[logical]
            field["representation"]["storage"] = {"kind": kind} | (
                {"length": 100} if kind == "my_varchar" else {}
            )
    document = contract(entry)
    document["target"] = {"family": dialect, "release": release}
    results = []
    for connector in ("sqlite.table", control):
        header = HEADER.replace("duckdb.arrow", connector)
        root = write(tmp_path / connector, PROJECTION, document, header)
        emission = compile_sql(
            root,
            module="main.pietto",
            kind="table",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
        # A blocker at the source ends where its connector's spelling ends.
        blockers = [
            b | {"location": b["location"] and b["location"] | {"end_column": None}}
            for b in json.loads(emission.document)["blockers"]
        ]
        results.append((emission.status, blockers))
    assert results[0] == results[1]
    status, blockers = results[0]
    details = [(b["code"], b["subject"]["detail"]) for b in blockers]
    assert status == "BLOCKED"
    assert ("PIE-B1001", "source_family_mismatch") in details
    assert ("PIE-B1006", "negative_original_target_evidence") in details
