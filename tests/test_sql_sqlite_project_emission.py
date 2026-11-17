"""SQLite project emission (docs/spec/sqlite-project-v1.md).

A project `sqlite.table` source checks; the PostgreSQL, MySQL and DuckDB
emitters refuse it with the blockers they give a source of another family,
and the SQLite adapter emits the tier 1 forms or refuses by its rules.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

import _pietto_sql_sqlite as sqlite
from _pietto_sql_duckdb import FIELDS, HEADER, PROJECTION, contract, source_entry, write
from pietto._project import project_sql_emission_cli as emission_cli
from pietto._project import project_sqlite_emission as adapter
from pietto._project import project_sqlite_sql as adapter_sql
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


FILTERED = """query result(m: Int, t: Text | None):
    from orders
    where amount > m and note == t or not ok and note is not None
    select:
        id
        n = m
        k = 1
        s = "a'b"
        f = ok == False
        g = t
    order by:
        amount desc
        note
    limit 5
"""
FILTERED_SQL = (
    "SELECT `s0`.`id` AS `id`, ?1 AS `n`, 1 AS `k`, 'a''b' AS `s`,"
    " `s0`.`ok` = 0 AS `f`, ?2 AS `g` FROM `main`.`orders` AS `s0`"
    " WHERE ((`s0`.`amount` > ?1) AND (`s0`.`note` COLLATE BINARY = ?2))"
    " OR ((NOT `s0`.`ok`) AND (`s0`.`note` IS NOT NULL))"
    " ORDER BY `s0`.`amount` DESC NULLS FIRST,"
    " `s0`.`note` COLLATE BINARY ASC NULLS LAST LIMIT 5"
)
GROUPED = """query result:
    from orders
    where note is not None
    group by:
        note
    select:
        note
        c = count()
        s = count(price)
        lo = min(id)
        hi = max(price)
        k = 2
    order by:
        c desc
        note
"""
GROUPED_SQL = (
    "SELECT `s0`.`note` AS `note`, COUNT(*) AS `c`, COUNT(`s0`.`price`) AS `s`,"
    " MIN(`s0`.`id`) AS `lo`, MAX(`s0`.`price`) AS `hi`, 2 AS `k`"
    " FROM `main`.`orders` AS `s0` WHERE `s0`.`note` IS NOT NULL"
    " GROUP BY `s0`.`note` COLLATE BINARY"
    " ORDER BY COUNT(*) DESC NULLS FIRST, `s0`.`note` COLLATE BINARY ASC NULLS LAST"
)


def emit(
    tmp_path: Path,
    body: str,
    document: dict[str, Any] | None = None,
    header: str = sqlite.HEADER,
    **options: str,
) -> tuple[str, dict[str, Any]]:
    root = sqlite.write(
        tmp_path / "project", body, document or sqlite.contract(), header
    )
    emission = compile_sql(
        root,
        module="main.pietto",
        kind=body.split(maxsplit=1)[0],
        name="result",
        dialect="sqlite",
        emission_contract="contract.json",
        **options,
    )
    return emission.status, json.loads(emission.document)


def details(document: dict[str, Any]) -> list[tuple[str, str]]:
    return [(b["code"], b["subject"]["detail"]) for b in document["blockers"]]


@pytest.mark.parametrize(
    ("body", "sql", "form"),
    [
        (sqlite.PROJECTION, sqlite.PROJECTION_SQL, "v1"),
        (FILTERED, FILTERED_SQL, "v2"),
        (GROUPED, GROUPED_SQL, "v1"),
        (
            "query result:\n    from orders\n    select:\n        c = count()\n"
            "        hi = max(id)\n",
            "SELECT COUNT(*) AS `c`, MAX(`s0`.`id`) AS `hi`"
            " FROM `main`.`orders` AS `s0`",
            "v1",
        ),
        (
            "query result(t: Text, p: Float):\n    from orders\n"
            '    where t <= note and p == price and note < "m"\n'
            "    select:\n        id\n",
            "SELECT `s0`.`id` AS `id` FROM `main`.`orders` AS `s0`"
            " WHERE ((?1 COLLATE BINARY <= `s0`.`note`) AND (?2 = `s0`.`price`))"
            " AND (`s0`.`note` COLLATE BINARY < 'm')",
            "v2",
        ),
    ],
)
def test_tier1_forms_emit_their_sql(
    tmp_path: Path, body: str, sql: str, form: str
) -> None:
    status, document = emit(tmp_path, body)
    assert (status, document["format"], document["sql"]) == (
        "VERIFIED",
        f"pietto.sql-emission.{form}",
        sql,
    )
    assert document["target"]["family"] == "sqlite"
    # The ranges cover the statement byte for byte, in order.
    ranges = document["ranges"]
    assert [r["start"] for r in ranges] == [0] + [r["end"] for r in ranges[:-1]]
    assert ranges[-1]["end"] == len(sql.encode("utf-8"))


def test_a_bool_literal_is_not_read_as_a_name(tmp_path: Path) -> None:
    """SQLite reads TRUE and FALSE as a column or a result alias so named."""
    document = sqlite.contract()
    document["sources"][0]["fields"][1]["column"] = "true"
    body = "query result:\n    from orders\n    where ok == True\n"
    body += "    select:\n        TRUE = id\n        f = False\n"
    status, document = emit(tmp_path, body, document)
    assert (status, document["sql"]) == (
        "VERIFIED",
        "SELECT `s0`.`id` AS `TRUE`, 0 AS `f` FROM `main`.`orders` AS `s0`"
        " WHERE `s0`.`ok` = 1",
    )


def test_the_document_numbers_and_describes_each_value(tmp_path: Path) -> None:
    status, document = emit(tmp_path, FILTERED)
    assert status == "VERIFIED"
    sql = document["sql"].encode("utf-8")
    uses = document["parameter_uses"]
    assert [
        (u["owner"]["parameter"], u["server_index"], u["physical_type"]) for u in uses
    ] == [
        (0, 1, "sqlite_integer"),
        (1, 2, "sqlite_text"),
        (0, 1, "sqlite_integer"),
        (1, 2, "sqlite_text"),
    ]
    assert [sql[u["range"]["start"] : u["range"]["end"]] for u in uses] == [
        b"?1",
        b"?2",
        b"?1",
        b"?2",
    ]
    assert [
        (p["name"], p["tag"], p["nullable"], len(p["reads"]))
        for p in (document["parameters"])
    ] == [("m", "Int", False, 2), ("t", "Text", True, 2)]
    generated = [r for r in document["requirements"] if r["denominator"] == "generated"]
    assert [(r["kind"], r["rule"], r["evidence"]) for r in generated] == [
        ("query_parameter", "R04", [{"parameter": j}]) for j in (0, 1, 0, 1)
    ]
    assert {
        r["rule"] for r in document["requirements"] if r["denominator"] == "original"
    } == {"sqlite_b2"}
    columns = {c["label"]: c for c in document["columns"]}
    int_full = {"kind": "int_range", "min": str(-(2**63)), "max": str(2**63 - 1)}
    assert columns["id"]["representation"] == sqlite.REPRESENTATIONS["Int"] | {
        "nullable": False
    }
    assert columns["id"]["correspondence"]["field"] == 0
    assert [
        (c["label"], c["logical_type"]["name"], c["representation"])
        for c in document["columns"][1:]
    ] == [
        (
            "n",
            "Int",
            {
                "storage": {"kind": "sqlite_integer"},
                "nullable": False,
                "domain": int_full,
            },
        ),
        (
            "k",
            "Int",
            {
                "storage": {"kind": "sqlite_integer"},
                "nullable": False,
                "domain": {"kind": "int_range", "min": "1", "max": "1"},
            },
        ),
        (
            "s",
            "Text",
            {
                "storage": {"kind": "sqlite_text"},
                "nullable": False,
                "domain": sqlite.REPRESENTATIONS["Text"]["domain"]
                | {"max_characters": 3},
            },
        ),
        (
            # A comparison's nullability `check` leaves unknown: nullable.
            "f",
            "Bool",
            {
                "storage": {"kind": "sqlite_bool01"},
                "nullable": True,
                "domain": {"kind": "bool01"},
            },
        ),
        (
            "g",
            "Text",
            {
                "storage": {"kind": "sqlite_text"},
                "nullable": True,
                "domain": sqlite.REPRESENTATIONS["Text"]["domain"]
                | {"max_characters": None},
            },
        ),
    ]
    assert [c["correspondence"]["sql_symbol"] for c in document["columns"]] == list(
        range(6)
    )


def test_grouped_columns_name_their_key_or_aggregate(tmp_path: Path) -> None:
    status, document = emit(tmp_path, GROUPED)
    assert status == "VERIFIED"
    columns = {c["label"]: c for c in document["columns"]}
    assert columns["note"]["representation"] == sqlite.REPRESENTATIONS["Text"] | {
        "nullable": True
    }
    assert columns["note"]["correspondence"]["group_key"]["kind"] == "group_key"
    assert columns["c"]["representation"] == {
        "storage": {"kind": "sqlite_integer"},
        "nullable": False,
        "domain": {"kind": "int_range", "min": "0", "max": str(2**63 - 1)},
    }
    # min and max keep their field's storage and domain, and may be NULL.
    assert columns["lo"]["representation"] == sqlite.REPRESENTATIONS["Int"] | {
        "nullable": True
    }
    assert columns["hi"]["representation"] == sqlite.REPRESENTATIONS["Float"] | {
        "nullable": True
    }
    assert {columns[k]["correspondence"]["aggregate"]["kind"] for k in "cs"} == {
        "aggregate"
    }


def test_the_command_prints_the_adapter_document(tmp_path: Path) -> None:
    root = sqlite.write(tmp_path / "project", FILTERED, sqlite.contract())
    argv = [
        f"--project={root}",
        "--module=main.pietto",
        "--kind=query",
        "--name=result",
        "--dialect=sqlite",
        "--emission-contract=contract.json",
    ]
    result = emission_cli.run_project_emit_sql([*argv, "--format=text"])
    assert (result.exit_code, result.stderr) == (0, "")
    text = result.stdout.decode()
    assert text.startswith("pietto.sql-emission.v2 VERIFIED\ntarget: sqlite 3.53.1\n")
    assert f"\nsql:\n{FILTERED_SQL}\nend sql\n" in text
    contract = sqlite.contract()
    contract["target"]["release"] = "3.45.0"
    (root / "contract.json").write_bytes(json.dumps(contract).encode())
    refused = emission_cli.run_project_emit_sql([*argv, "--format=text"])
    assert refused.exit_code == 1 and refused.stdout == b""
    assert refused.stderr.splitlines()[1:3] == [
        "blocker PIE-B1003 UNSUPPORTED_RULE: target_release_not_reviewed",
        '  hint: the reviewed sqlite release is "3.53.1"',
    ]


def _contract(change: str) -> dict[str, Any]:
    document = sqlite.contract()
    entry, environment = document["sources"][0], document["environment"]
    fields = entry["fields"]
    if change == "namespace":
        entry["relation"]["namespace"] = "public"
    elif change == "mismatch":
        entry["relation"]["name"] = "Orders"
    elif change == "folded":
        fields[2]["column"] = "ID"
    elif change == "nullable":
        fields[0]["representation"]["nullable"] = True
    elif change == "storage":
        fields[1]["representation"]["storage"] = {"kind": "sqlite_real"}
    elif change == "collation":
        fields[2]["representation"]["domain"]["collation"] = "NOCASE"
    elif change == "encoding":
        environment[0]["value"] = "UTF8"
    elif change == "operators":
        del environment[1]
    elif change == "protocol":
        environment[2]["value"] = "postgres_extended"
    elif change == "release":
        document["target"]["release"] = "3.45.0"
    elif change == "identifier_case":
        environment.append(
            {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
        )
    elif change == "row_domain":
        entry["premises"] = entry["premises"][1:]
    elif change == "columns":
        environment.append(
            {"key": "resource_limits", "scope": "statement", "value": {"columns": 4}}
        )
    return document


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("release", [("PIE-B1003", "target_release_not_reviewed")]),
        ("identifier_case", [("PIE-B1003", "premise_not_admitted_on_target")]),
        ("operators", [("PIE-B1004", "operator_environment_declaration_missing")]),
        ("protocol", [("PIE-B1005", "parameter_protocol_declaration_mismatch")]),
        ("columns", [("PIE-B1007", "generated_structure_limit")]),
        ("namespace", [("PIE-B1001", "source_identifier_unrepresentable")]),
        ("mismatch", [("PIE-B1001", "sqlite_table_name_mismatch")]),
        ("row_domain", [("PIE-B1001", "row_domain_matches_declaration_required")]),
        ("encoding", [("PIE-B1005", "client_encoding_mismatch")]),
        ("folded", [("PIE-B1001", "column_identifier_unrepresentable_or_colliding")]),
        ("nullable", [("PIE-B1002", "nullability_mismatch")]),
        ("storage", [("PIE-B1002", "physical_storage_or_domain_mismatch")]),
        ("collation", [("PIE-B1002", "physical_storage_or_domain_mismatch")]),
    ],
)
def test_contract_refusals(
    tmp_path: Path, change: str, expected: list[tuple[str, str]]
) -> None:
    status, document = emit(tmp_path, FILTERED, _contract(change))
    assert (status, details(document)) == ("BLOCKED", expected)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "query result:\n    from orders\n    select distinct:\n        note\n",
            [("PIE-B1003", "sqlite_relation_shape_not_admitted", 12)],
        ),
        (
            "query result:\n    from orders\n    where amount + 1 > 3\n"
            "    select:\n        id\n        s = -1\n",
            [("PIE-B1003", "sqlite_expression_not_admitted", 12)],
        ),
        (
            "query result:\n    from orders\n    where price > 1\n"
            "    select:\n        id\n",
            [("PIE-B1003", "sqlite_expression_not_admitted", 12)],
        ),
        (
            "query result:\n    from orders\n    group by:\n        note\n"
            "    select:\n        note\n        c = count() + 1\n"
            "        t = sum(amount)\n",
            [
                ("PIE-B1003", "sqlite_expression_not_admitted", 16),
                ("PIE-B1003", "sqlite_aggregate_not_admitted", 16),
                ("PIE-B1003", "sqlite_projection_not_admitted", 16),
                ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 17),
            ],
        ),
        (
            "query result:\n    from orders\n    group by:\n        note\n"
            "    select:\n        note\n        d = abs(max(id))\n",
            [
                ("PIE-B1003", "sqlite_expression_not_admitted", 16),
                ("PIE-B1003", "sqlite_aggregate_not_admitted", 16),
                ("PIE-B1003", "sqlite_projection_not_admitted", 16),
            ],
        ),
        (
            "query result:\n    from orders\n    group by:\n        note\n"
            "    select:\n        note\n        a = avg(price)\n"
            "        d = count_distinct(price)\n        s = sum(price)\n",
            [("PIE-B1003", "sqlite_aggregate_not_admitted", 16)],
        ),
    ],
)
def test_statement_refusals_at_their_first_site(
    tmp_path: Path, body: str, expected: list[tuple[str, str, int]]
) -> None:
    status, document = emit(tmp_path, body)
    assert status == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"])
        for b in document["blockers"]
    ] == expected


HAVING = """query result(v: Int, t: Text):
    from orders
    where amount > v
    group by:
        note
        ok
    select:
        note
        ok
        amount = count()
        d = count_distinct(note)
        a = avg(amount)
        s = sum(id)
    having amount > v and ok == True or note < t and a > 1.5 and s >= 0
    order by:
        d desc
        a
    limit 3
"""
# HAVING writes each key and aggregate itself, never the output alias
# `amount`, which also names a column; `id`'s int_range lies above zero.
HAVING_SQL = (
    "SELECT `s0`.`note` AS `note`, `s0`.`ok` AS `ok`, COUNT(*) AS `amount`,"
    " COUNT(DISTINCT `s0`.`note` COLLATE BINARY) AS `d`,"
    " AVG(CAST(`s0`.`amount` AS REAL)) AS `a`, SUM(`s0`.`id`) AS `s`"
    " FROM `main`.`orders` AS `s0` WHERE `s0`.`amount` > ?1"
    " GROUP BY `s0`.`note` COLLATE BINARY, `s0`.`ok`"
    " HAVING ((COUNT(*) > ?1) AND (`s0`.`ok` = 1))"
    " OR (((`s0`.`note` COLLATE BINARY < ?2)"
    " AND (AVG(CAST(`s0`.`amount` AS REAL)) > 1.5)) AND (SUM(`s0`.`id`) >= 0))"
    " ORDER BY COUNT(DISTINCT `s0`.`note` COLLATE BINARY) DESC NULLS FIRST,"
    " AVG(CAST(`s0`.`amount` AS REAL)) ASC NULLS LAST LIMIT 3"
)


def _ranged(low: str, high: str) -> dict[str, Any]:
    """The contract with `id`'s int_range from `low` to `high`."""
    document = sqlite.contract()
    domain = document["sources"][0]["fields"][0]["representation"]["domain"]
    domain.update(min=low, max=high)
    return document


def test_tier2_aggregates_and_having_emit_their_sql(tmp_path: Path) -> None:
    status, document = emit(tmp_path, HAVING, _ranged("0", str(2**63 - 1)))
    assert (status, document["format"], document["sql"]) == (
        "VERIFIED",
        "pietto.sql-emission.v2",
        HAVING_SQL,
    )
    ranges = document["ranges"]
    assert [r["start"] for r in ranges] == [0] + [r["end"] for r in ranges[:-1]]
    assert ranges[-1]["end"] == len(HAVING_SQL.encode("utf-8"))
    # A HAVING parameter is numbered by its first read, after the WHERE's.
    assert [
        (u["owner"]["parameter"], u["server_index"], u["physical_type"])
        for u in document["parameter_uses"]
    ] == [(0, 1, "sqlite_integer"), (0, 1, "sqlite_integer"), (1, 2, "sqlite_text")]
    columns = {c["label"]: c for c in document["columns"]}
    counted = {"kind": "int_range", "min": "0", "max": str(2**63 - 1)}
    full = {"kind": "int_range", "min": str(-(2**63)), "max": str(2**63 - 1)}
    real = {"kind": "finite_float", "format": "binary64"}
    assert [
        (
            label,
            columns[label]["logical_type"]["name"],
            columns[label]["representation"],
            columns[label]["correspondence"]["aggregate"]["kind"],
        )
        for label in ("amount", "d", "a", "s")
    ] == [
        (
            "amount",
            "Int",
            {
                "storage": {"kind": "sqlite_integer"},
                "nullable": False,
                "domain": counted,
            },
            "aggregate",
        ),
        (
            "d",
            "Int",
            {
                "storage": {"kind": "sqlite_integer"},
                "nullable": False,
                "domain": counted,
            },
            "aggregate",
        ),
        (
            "a",
            "Float",
            {"storage": {"kind": "sqlite_real"}, "nullable": True, "domain": real},
            "aggregate",
        ),
        (
            "s",
            "Int",
            {"storage": {"kind": "sqlite_integer"}, "nullable": True, "domain": full},
            "aggregate",
        ),
    ]


@pytest.mark.parametrize(
    ("low", "high", "admitted"),
    [
        ("0", str(2**63 - 1), True),
        ("5", "9", True),
        (str(-(2**63)), "0", True),
        ("-7", "-1", True),
        ("-1", "1", False),
        (str(-(2**63)), str(2**63 - 1), False),
    ],
)
def test_sum_needs_an_int_range_on_one_side_of_zero(
    tmp_path: Path, low: str, high: str, admitted: bool
) -> None:
    """SQLite fails a sum once a partial sum leaves signed 64 bits, so a sum
    over values of both signs may fail where the exact sum fits; over one
    sign every partial sum lies between zero and the result."""
    body = "query result:\n    from orders\n    group by:\n        ok\n"
    body += "    select:\n        ok\n        s = sum(id)\n        n = count()\n"
    status, document = emit(tmp_path, body, _ranged(low, high))
    if admitted:
        assert (status, document["sql"]) == (
            "VERIFIED",
            "SELECT `s0`.`ok` AS `ok`, SUM(`s0`.`id`) AS `s`, COUNT(*) AS `n`"
            " FROM `main`.`orders` AS `s0` GROUP BY `s0`.`ok`",
        )
        return
    assert status == "BLOCKED"
    (blocker,) = document["blockers"]
    assert (blocker["code"], blocker["subject"]["detail"]) == (
        "PIE-B1004",
        "sum_int_aggregate_range_proof_missing",
    )
    assert blocker["location"]["line"] == 16
    assert blocker["suggestion"] == (
        "declare an int_range on one side of zero, or keep this sum in"
        " check/plan: SQLite can fail a sum over values of both signs whose"
        " result fits"
    )


def test_a_sum_over_an_unfitting_field_has_no_range_rule(tmp_path: Path) -> None:
    """Rule 35 reads only a field that passes rule 33; a `Float` sum is rule 10."""
    document = _ranged("-1", "1")
    document["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "sqlite_real"
    }
    body = "query result:\n    from orders\n    select:\n        s = sum(id)\n"
    status, refused = emit(tmp_path, body, document)
    assert (status, details(refused)) == (
        "BLOCKED",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    )


def test_field_and_parameter_types_outside_the_tier(tmp_path: Path) -> None:
    header = sqlite.HEADER.replace("price: Float", "price: Decimal(10, 2)")
    body = "query result(d: Decimal(10, 2)):\n    from orders\n    select:\n"
    body += "        id\n        x = d\n"
    status, document = emit(tmp_path, body, header=header)
    assert (status, details(document)) == (
        "BLOCKED",
        [
            ("PIE-B1003", "sqlite_field_type_not_admitted"),
            ("PIE-B1003", "sqlite_parameter_not_admitted"),
            ("PIE-B1002", "physical_storage_or_domain_mismatch"),
        ],
    )


def test_unrelated_refusals_stay_beside_the_sqlite_ones(tmp_path: Path) -> None:
    """Rules 1-35 are checked together: a statement refused for an unrelated
    reason, a bind-safe policy and a contract that misnames the table, keeps
    each refusal in rule order."""
    body = "query result:\n    from orders\n    where amount + 1 > 3\n"
    body += "    select:\n        id\n"
    status, document = emit(
        tmp_path, body, _contract("mismatch"), literal_policy="bind-safe"
    )
    assert (status, details(document)) == (
        "BLOCKED",
        [
            ("PIE-B1003", "literal_policy_not_admitted_on_target"),
            ("PIE-B1003", "sqlite_expression_not_admitted"),
            ("PIE-B1001", "sqlite_table_name_mismatch"),
        ],
    )


def test_a_source_of_another_family_and_contract_schema_errors(
    tmp_path: Path,
) -> None:
    header = sqlite.HEADER.replace('sqlite.table("orders")', 'postgres.table("orders")')
    status, document = emit(tmp_path / "family", sqlite.PROJECTION, header=header)
    assert status == "BLOCKED"
    assert ("PIE-B1001", "source_family_mismatch") in details(document)
    assert ("PIE-B1006", "negative_original_target_evidence") in details(document)
    duplicate = sqlite.contract()
    duplicate["sources"][0]["fields"][2]["column"] = "id"
    # An exact duplicate column, and a DuckDB contract whose target, scan and
    # storages are another family's.
    for path, document, expected in (
        ("columns", duplicate, ["sources/0/fields/2/column"]),
        ("target", contract(), ["target/family", "sources/0/scan"]),
    ):
        status, refused = emit(tmp_path / path, sqlite.PROJECTION, document)
        assert status == "INPUT_REJECTED"
        assert {e["kind"] for e in refused["cli_errors"]} == {
            "emission_contract_schema"
        }
        paths = [e["path"] for e in refused["cli_errors"]]
        assert paths[: len(expected)] == expected


def test_the_verifier_refuses_a_changed_artifact(tmp_path: Path) -> None:
    root = sqlite.write(tmp_path / "project", GROUPED, sqlite.contract())
    outcome, _ = emission_cli.emit_project(
        root,
        "main.pietto",
        "query",
        "result",
        "sqlite",
        "contract.json",
        emission_cli.POLICIES["preserve"],
    )
    assert type(outcome) is adapter.SQLiteEmission and outcome.artifact is not None
    artifact = outcome.artifact
    assert adapter.verify_artifact(artifact)
    ast = artifact.ast
    changed = (
        dataclasses.replace(artifact, sql=artifact.sql.replace(b"DESC", b"ASC ")),
        dataclasses.replace(artifact, ast=dataclasses.replace(ast, order_by=())),
        dataclasses.replace(
            artifact, ast=dataclasses.replace(ast, group_by=ast.group_by[:0])
        ),
        dataclasses.replace(artifact, document=artifact.document.replace(b"2", b"3")),
    )
    for item in changed:
        assert not adapter.verify_artifact(item)
        document = json.loads(
            emission_cli.serialize_emission(dataclasses.replace(outcome, artifact=item))
        )
        assert details(document) == [("PIE-B1008", "artifact_correspondence")]
    # The AST's own rules keep a HAVING to GROUP BY keys and aggregates, with
    # COLLATE BINARY at a Text comparison and a count_distinct of a Text.
    labels = tuple(result.label for result in ast.results)

    def holds(having: object, **change: object) -> bool:
        changed = dataclasses.replace(ast, having=having, **change)
        return adapter_sql.ast_rules_hold(changed, labels, frozenset({2}), frozenset())

    key, one = ast.group_by[0].value, adapter_sql.SQLiteLiteral(1, None)
    assert type(key) is adapter_sql.SQLiteColumn
    count = adapter_sql.SQLiteAggregate("count", None, False, None)
    distinct = adapter_sql.SQLiteAggregate("count_distinct", key, True, None)
    assert holds(adapter_sql.SQLiteComparison(">", distinct, one, False, None))
    text = adapter_sql.SQLiteComparison(
        "=", key, adapter_sql.SQLiteLiteral("a", None), True, None
    )
    assert holds(text)
    assert not holds(dataclasses.replace(text, collate=False))
    assert not holds(adapter_sql.SQLiteNot(text, None))
    assert not holds(adapter_sql.SQLiteIsNull(key, False, None))
    assert not holds(
        adapter_sql.SQLiteComparison(
            ">", dataclasses.replace(distinct, collate=False), one, False, None
        )
    )
    assert not holds(
        adapter_sql.SQLiteComparison(
            ">", adapter_sql.SQLiteColumn(0, None), one, False, None
        )
    )
    assert not holds(
        adapter_sql.SQLiteComparison(">", count, one, False, None), group_by=()
    )
