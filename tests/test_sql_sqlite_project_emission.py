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
            [("PIE-B1004", "int_arithmetic_range_proof_missing", 12)],
        ),
        (
            "query result:\n    from orders\n    where price > 1\n"
            "    select:\n        id\n",
            [("PIE-B1003", "sqlite_expression_not_admitted", 12)],
        ),
        # Rule 9b sorts after rule 9 and before rule 10, wherever its site.
        (
            "query result(p: Int):\n    from orders\n    select:\n"
            "        v = amount + 1\n        w = p + 1\n",
            [
                ("PIE-B1003", "sqlite_expression_not_admitted", 14),
                ("PIE-B1004", "int_arithmetic_range_proof_missing", 13),
            ],
        ),
        (
            "query result:\n    from orders\n    select:\n"
            "        c = count(amount + 1)\n",
            [
                ("PIE-B1004", "int_arithmetic_range_proof_missing", 13),
                ("PIE-B1003", "sqlite_aggregate_not_admitted", 13),
            ],
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


INT_MIN, INT_MAX = -(2**63), 2**63 - 1
ROOT = 3037000499  # the largest Int whose square fits signed 64 bits
ARITHMETIC = """query result:
    from orders
    where -(amount * 2) < id - 1 and amount > -9223372036854775808
    select:
        id
        a = abs(amount - 1) + id * 3
        k = -1
"""
# Every non-atom operand is in parentheses, so a unary minus is never `--`,
# and the minimum is one signed literal, which SQLite reads as an INTEGER.
ARITHMETIC_SQL = (
    "SELECT `s0`.`id` AS `id`, ABS(`s0`.`amount` - 1) + (`s0`.`id` * 3) AS `a`,"
    " -1 AS `k` FROM `main`.`orders` AS `s0`"
    " WHERE ((-(`s0`.`amount` * 2)) < (`s0`.`id` - 1))"
    " AND (`s0`.`amount` > (-9223372036854775808))"
)
SUMMED = """query result:
    from orders
    where amount - 1 > 0
    group by:
        ok
    select:
        ok
        s = sum(amount * id)
        a = avg(amount - id)
"""
SUMMED_SQL = (
    "SELECT `s0`.`ok` AS `ok`, SUM(`s0`.`amount` * `s0`.`id`) AS `s`,"
    " AVG(CAST(`s0`.`amount` - `s0`.`id` AS REAL)) AS `a`"
    " FROM `main`.`orders` AS `s0` WHERE (`s0`.`amount` - 1) > 0"
    " GROUP BY `s0`.`ok`"
)


def _ranges(**bounds: tuple[int, int]) -> dict[str, Any]:
    """The contract with an `int_range` for each named `Int` field."""
    document = sqlite.contract()
    for field in document["sources"][0]["fields"]:
        if field["name"] in bounds:
            low, high = bounds[field["name"]]
            field["representation"]["domain"].update(min=str(low), max=str(high))
    return document


@pytest.mark.parametrize(
    ("body", "document", "sql"),
    [
        (ARITHMETIC, _ranges(amount=(-10, 10), id=(0, 100)), ARITHMETIC_SQL),
        (SUMMED, _ranges(amount=(0, ROOT), id=(0, ROOT)), SUMMED_SQL),
    ],
)
def test_range_proved_int_arithmetic_emits_its_sql(
    tmp_path: Path, body: str, document: dict[str, Any], sql: str
) -> None:
    status, emitted = emit(tmp_path, body, document)
    assert (status, emitted["sql"]) == ("VERIFIED", sql)
    ranges = emitted["ranges"]
    assert [r["start"] for r in ranges] == [0] + [r["end"] for r in ranges[:-1]]
    assert ranges[-1]["end"] == len(sql.encode("utf-8"))
    # An arithmetic or `sum` column has the widest `Int` domain.
    full = {"kind": "int_range", "min": str(INT_MIN), "max": str(INT_MAX)}
    for column in emitted["columns"][1:]:
        if column["logical_type"]["name"] == "Int":
            assert column["representation"]["domain"] == full, column


@pytest.mark.parametrize(
    ("value", "low", "high", "admitted"),
    [
        ("amount + 1", INT_MIN, INT_MAX - 1, True),
        ("amount + 1", INT_MIN, INT_MAX, False),
        ("amount - 1", INT_MIN + 1, INT_MAX, True),
        ("amount - 1", INT_MIN, INT_MAX, False),
        ("amount * 2", INT_MIN // 2, INT_MAX // 2, True),
        ("amount * 2", INT_MIN // 2, INT_MAX // 2 + 1, False),
        ("amount * -2", INT_MIN // 2 + 1, -(INT_MIN // 2), True),
        ("amount * -2", INT_MIN // 2, 0, False),
        ("-amount", INT_MIN + 1, INT_MAX, True),
        ("-amount", INT_MIN, 0, False),
        ("abs(amount)", INT_MIN + 1, 0, True),
        ("abs(amount)", INT_MIN, INT_MAX, False),
        # Two fields: every corner counts, `id` running from 0 to 2.
        ("amount * id", -(2**62), 1, True),
        ("amount * id", -(2**62) - 1, 1, False),
        ("amount + id", 0, INT_MAX - 2, True),
        ("amount + id", 0, INT_MAX - 1, False),
        ("amount - id", INT_MIN + 2, 0, True),
        ("amount - id", INT_MIN + 1, 0, False),
        # Each intermediate result too: SQLite would go on with a REAL.
        ("(amount + 1) - 2", 0, INT_MAX - 1, True),
        ("(amount + 1) - 2", 0, INT_MAX, False),
        ("-9223372036854775807 - 1", 0, 0, True),
        ("-9223372036854775808 - 1", 0, 0, False),
        ("abs(-9223372036854775808)", 0, 0, False),
        ("-(-9223372036854775808)", 0, 0, False),
    ],
)
def test_int_arithmetic_needs_every_bound_inside_signed_64_bits(
    tmp_path: Path, value: str, low: int, high: int, admitted: bool
) -> None:
    body = f"query result:\n    from orders\n    select:\n        id\n        v = {value}\n"
    status, document = emit(tmp_path, body, _ranges(amount=(low, high), id=(0, 2)))
    if admitted:
        assert status == "VERIFIED", document["blockers"]
        return
    assert status == "BLOCKED"
    (blocker,) = document["blockers"]
    assert (blocker["code"], blocker["subject"]["detail"]) == (
        "PIE-B1004",
        "int_arithmetic_range_proof_missing",
    )
    assert blocker["location"]["line"] == 14
    assert blocker["suggestion"] == (
        "declare int_range bounds that keep every operand and result inside"
        " signed 64 bits, or keep this expression in check/plan: SQLite turns an"
        " Int overflow into a REAL without an error"
    )


@pytest.mark.parametrize(
    ("value", "high", "expected"),
    [
        ("sum(amount * id)", ROOT, []),
        ("sum(-amount)", ROOT, []),
        (
            "sum(amount - id)",
            ROOT,
            [("PIE-B1004", "sum_int_aggregate_range_proof_missing")],
        ),
        # Each row's argument too: SQLite sums a REAL without an error.
        (
            "sum(amount + 1)",
            INT_MAX,
            [("PIE-B1004", "int_arithmetic_range_proof_missing")],
        ),
        (
            "avg(amount + 1)",
            INT_MAX,
            [("PIE-B1004", "int_arithmetic_range_proof_missing")],
        ),
        # Rule 35 yields to rule 9b inside the argument, though the argument
        # runs from -1 to 9223372036854775806.
        (
            "sum((amount + 1) - 2)",
            INT_MAX,
            [("PIE-B1004", "int_arithmetic_range_proof_missing")],
        ),
        ("count(amount + 1)", ROOT, [("PIE-B1003", "sqlite_aggregate_not_admitted")]),
    ],
)
def test_an_aggregate_argument_is_proved_row_by_row_and_a_sum_one_sided(
    tmp_path: Path, value: str, high: int, expected: list[tuple[str, str]]
) -> None:
    """`amount` runs from 0 to `high` and `id` from 0 to ROOT."""
    body = f"query result:\n    from orders\n    select:\n        s = {value}\n"
    document = _ranges(amount=(0, high), id=(0, ROOT))
    status, emitted = emit(tmp_path, body, document)
    found = details(emitted) if status == "BLOCKED" else []
    assert (status, found) == ("BLOCKED" if expected else "VERIFIED", expected)


@pytest.mark.parametrize(
    "value",
    [
        "amount + p",
        "price * 2.0",
        "amount / 2",
        "amount % 2",
        "+amount",
        "9223372036854775808",
        "0 - 9223372036854775808",
        "-9223372036854775809",
        "amount + 9223372036854775808",
        "amount * -9223372036854775809",
    ],
)
def test_arithmetic_outside_the_tier_is_rule_9(tmp_path: Path, value: str) -> None:
    """Parameters, Float operands, `/`, `%` and unary `+` stay refused, and so
    does 9223372036854775808 anywhere but right after a unary minus, with no
    range rule over a literal that rule 9 refuses."""
    body = "query result(p: Int):\n    from orders\n    select:\n        id\n"
    status, document = emit(tmp_path, body + f"        v = {value}\n")
    assert (status, details(document)) == (
        "BLOCKED",
        [("PIE-B1003", "sqlite_expression_not_admitted")],
    )


def test_arithmetic_over_an_unfitting_field_has_no_range_rule(tmp_path: Path) -> None:
    """Rule 9b reads only fields that pass rule 33, as rule 35 does."""
    document = sqlite.contract()
    document["sources"][0]["fields"][1]["representation"]["storage"] = {
        "kind": "sqlite_real"
    }
    body = "query result:\n    from orders\n    select:\n        v = amount + 1\n"
    status, refused = emit(tmp_path, body, document)
    assert (status, details(refused)) == (
        "BLOCKED",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    )


def test_the_sql_ast_writes_no_comment_and_the_minimum_once() -> None:
    """A unary minus before a minus is in parentheses, never `--`, which
    starts a comment, and 9223372036854775808 is a literal only right after
    a unary minus, where SQLite reads the INTEGER minimum. Only `avg` and
    `sum` read arithmetic; every other aggregate reads a column."""
    sql = adapter_sql
    column, five = sql.SQLiteColumn(0, None), sql.SQLiteLiteral(5, None)
    minimum = sql.SQLiteLiteral(2**63, None)
    values = (
        sql.SQLiteNegative(minimum, None),
        sql.SQLiteNegative(sql.SQLiteNegative(five, None), None),
        sql.SQLiteArithmetic("-", column, sql.SQLiteNegative(five, None), None),
        sql.SQLiteNegative(sql.SQLiteAbs(column, None), None),
    )
    results = tuple(
        sql.SQLiteResult(value, label, None, None)
        for value, label in zip(values, "abcd")
    )
    select = sql.SQLiteSelect(
        "t", ("x",), results, None, (), None, (), None, None, None
    )
    rendered, _tokens = sql.render(select)
    assert rendered == (
        b"SELECT -9223372036854775808 AS `a`, -(-5) AS `b`, `s0`.`x` - (-5) AS `c`,"
        b" -ABS(`s0`.`x`) AS `d` FROM `main`.`t` AS `s0`"
    )
    labels = tuple("abcd")
    assert sql.ast_rules_hold(select, labels, frozenset(), frozenset())
    negative = sql.SQLiteNegative(column, None)
    for function in ("avg", "sum"):
        total = dataclasses.replace(
            select,
            results=(
                sql.SQLiteResult(
                    sql.SQLiteAggregate(function, negative, False, None),
                    "a",
                    None,
                    None,
                ),
            ),
        )
        assert sql.ast_rules_hold(total, ("a",), frozenset(), frozenset())
    for value in (
        minimum,
        sql.SQLiteArithmetic("/", column, five, None),
        sql.SQLiteNegative(sql.SQLiteLiteral(2**63 + 1, None), None),
        sql.SQLiteAggregate("min", negative, False, None),
        sql.SQLiteAggregate("count", negative, False, None),
    ):
        changed = dataclasses.replace(
            select, results=(dataclasses.replace(results[0], value=value),)
        )
        assert not sql.ast_rules_hold(changed, ("a",), frozenset(), frozenset())


WINDOWED = """query result(v: Int):
    from orders
    where amount > v
    select:
        id
        r = rank() window(partition by note order by amount desc)
        d = dense_rank() window(order by ok, price desc)
        n = row_number() window(partition by ok order by id)
        c = count() window(partition by note)
        k = count(price) window(order by id rows between 2 preceding and 1 following)
        lo = min(id) window(order by note groups between 1 preceding and current row)
        hi = max(price) window(order by id range between current row and unbounded following)
        s = sum(id) window(order by id)
        t = sum(id) window(partition by ok)
    order by:
        id
    limit 5
"""
# Each window inline, with the frame the plan resolves written out: an
# omitted frame is RANGE from UNBOUNDED PRECEDING to CURRENT ROW, which is
# the whole partition without ORDER BY.
WINDOWED_SQL = (
    "SELECT `s0`.`id` AS `id`, RANK() OVER (PARTITION BY `s0`.`note` COLLATE"
    " BINARY ORDER BY `s0`.`amount` DESC NULLS FIRST) AS `r`, DENSE_RANK() OVER"
    " (ORDER BY `s0`.`ok` ASC NULLS LAST, `s0`.`price` DESC NULLS FIRST) AS `d`,"
    " ROW_NUMBER() OVER (PARTITION BY `s0`.`ok` ORDER BY `s0`.`id` ASC NULLS"
    " LAST) AS `n`, COUNT(*) OVER (PARTITION BY `s0`.`note` COLLATE BINARY RANGE"
    " BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS `c`, COUNT(`s0`.`price`)"
    " OVER (ORDER BY `s0`.`id` ASC NULLS LAST ROWS BETWEEN 2 PRECEDING AND 1"
    " FOLLOWING) AS `k`, MIN(`s0`.`id`) OVER (ORDER BY"
    " `s0`.`note` COLLATE BINARY ASC NULLS LAST GROUPS BETWEEN 1 PRECEDING AND"
    " CURRENT ROW) AS `lo`, MAX(`s0`.`price`) OVER (ORDER BY"
    " `s0`.`id` ASC NULLS LAST RANGE BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING"
    ") AS `hi`, SUM(`s0`.`id`) OVER (ORDER BY `s0`.`id` ASC NULLS"
    " LAST RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS `s`,"
    " SUM(`s0`.`id`) OVER (PARTITION BY `s0`.`ok` RANGE BETWEEN UNBOUNDED"
    " PRECEDING AND CURRENT ROW) AS `t` FROM `main`.`orders` AS `s0`"
    " WHERE `s0`.`amount` > ?1 ORDER BY `s0`.`id` ASC NULLS LAST LIMIT 5"
)


def test_windows_over_one_source_emit_their_sql(tmp_path: Path) -> None:
    status, document = emit(tmp_path, WINDOWED, _ranged("0", str(2**63 - 1)))
    assert (status, document["sql"]) == ("VERIFIED", WINDOWED_SQL)
    ranges = document["ranges"]
    assert [r["start"] for r in ranges] == [0] + [r["end"] for r in ranges[:-1]]
    assert ranges[-1]["end"] == len(WINDOWED_SQL.encode("utf-8"))
    columns = {c["label"]: c for c in document["columns"]}
    full = sqlite.REPRESENTATIONS["Int"]["domain"]
    domains = {
        label: {"kind": "int_range", "min": low, "max": str(2**63 - 1)}
        for label, low in (("r", "1"), ("d", "1"), ("n", "1"), ("c", "0"), ("k", "0"))
    }
    domains |= {
        "lo": {"kind": "int_range", "min": "0", "max": str(2**63 - 1)},
        "hi": sqlite.REPRESENTATIONS["Float"]["domain"],
        "s": full,
        "t": full,
    }
    assert {
        label: columns[label]["representation"]["domain"] for label in domains
    } == domains
    assert [columns[label]["nullable"] for label in domains] == [False] * 5 + [True] * 4
    assert {
        columns[label]["correspondence"]["window"]["kind"] for label in domains
    } == {"window"}


@pytest.mark.parametrize(
    ("select", "expected"),
    [
        # A named window, a function outside the tier, a Text argument, a
        # RANGE offset and an exclude are rule 5b.
        (
            "        r = row_number() window w\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = ntile(2) window(order by id)\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = lag(id) window(order by id)\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = avg(amount) window()\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = count(note) window()\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        # With no key, `count()` counts rows in their scan order in any
        # frame but the default (D78.16).
        (
            "        r = count() window(rows between 1 preceding and current row)\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = max(id) window(order by id range between 1 preceding"
            " and current row)\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        (
            "        r = count() window(order by id rows between 1 preceding"
            " and current row exclude current row)\n",
            [("PIE-B1003", "sqlite_window_not_admitted", 15)],
        ),
        # A sliding sum is rule 5c even over a one-sided range, and a mixed
        # range is rule 35 at the window.
        (
            "        s = sum(id) window(order by id rows between 1 preceding"
            " and current row)\n"
            "        t = sum(id) window(order by id rows between current row"
            " and unbounded following)\n",
            [("PIE-B1003", "sqlite_window_sum_frame_not_admitted", 15)],
        ),
        (
            "        s = sum(amount) window(order by id)\n",
            [("PIE-B1004", "sum_int_aggregate_range_proof_missing", 15)],
        ),
    ],
)
def test_window_refusals_at_their_first_site(
    tmp_path: Path, select: str, expected: list[tuple[str, str, int]]
) -> None:
    body = "query result:\n    from orders\n    let w = window(order by id)\n"
    body += "    select:\n        id\n" + select
    status, document = emit(tmp_path, body, _ranged("0", str(2**63 - 1)))
    assert status == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"])
        for b in document["blockers"]
    ] == expected


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "    group by:\n        note\n    select:\n        note\n"
            "        c = count()\n        r = rank() window(order by note)\n",
            [
                ("PIE-B1003", "sqlite_relation_shape_not_admitted"),
                ("PIE-B1003", "sqlite_window_not_admitted"),
                ("PIE-B1003", "sqlite_projection_not_admitted"),
            ],
        ),
        # A window that reads no key or argument is still over grouped rows.
        (
            "    group by:\n        note\n    select:\n        note\n"
            "        k = count()\n        c = count() window()\n",
            [
                ("PIE-B1003", "sqlite_relation_shape_not_admitted"),
                ("PIE-B1003", "sqlite_window_not_admitted"),
                ("PIE-B1003", "sqlite_projection_not_admitted"),
            ],
        ),
        (
            "    select:\n        id\n        r = row_number() window(order by id)\n"
            "    qualify r < 3\n",
            [("PIE-B1003", "sqlite_relation_shape_not_admitted")],
        ),
        (
            "    select:\n        id\n        r = row_number() window(order by id)\n"
            "    order by:\n        r\n",
            [("PIE-B1003", "sqlite_order_not_admitted")],
        ),
    ],
)
def test_windows_stay_refused_over_groups_qualify_and_their_order(
    tmp_path: Path, body: str, expected: list[tuple[str, str]]
) -> None:
    status, document = emit(tmp_path, "query result:\n    from orders\n" + body)
    assert (status, details(document)) == ("BLOCKED", expected)


def test_exclude_no_others_is_left_out(tmp_path: Path) -> None:
    """`exclude no others` excludes nothing, so its SQL is the frame's."""
    frame = "order by id rows between 1 preceding and current row"
    sql = []
    for exclude in ("", " exclude no others"):
        body = "query result:\n    from orders\n    select:\n"
        body += f"        c = count() window({frame}{exclude})\n"
        status, document = emit(tmp_path / str(len(sql)), body)
        assert status == "VERIFIED"
        sql.append(document["sql"])
    assert sql[0] == sql[1]
    assert "EXCLUDE" not in sql[1]


def test_a_window_needs_the_operator_environment(tmp_path: Path) -> None:
    body = "query result:\n    from orders\n    select:\n"
    body += "        r = count() window()\n"
    status, document = emit(tmp_path, body, _contract("operators"))
    assert (status, details(document)) == (
        "BLOCKED",
        [("PIE-B1004", "operator_environment_declaration_missing")],
    )


def test_the_ast_rules_keep_each_window_to_its_tier(tmp_path: Path) -> None:
    """The AST's own window rules: a `sum` in a monotone frame, a ranking
    without a frame, `COLLATE BINARY` at a `Text` key, and no GROUP BY or
    aggregate beside a window."""
    root = sqlite.write(tmp_path / "project", WINDOWED, _ranged("0", str(2**63 - 1)))
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
    ast = outcome.artifact.ast
    labels = tuple(result.label for result in ast.results)

    def window(label: str) -> adapter_sql.SQLiteWindow:
        (value,) = (result.value for result in ast.results if result.label == label)
        assert type(value) is adapter_sql.SQLiteWindow
        return value

    def holds(label: str, value: object, **change: object) -> bool:
        results = tuple(
            dataclasses.replace(r, value=value) if r.label == label else r
            for r in ast.results
        )
        changed = dataclasses.replace(ast, results=results, **change)
        texts = frozenset({(0, 2)})
        return adapter_sql.ast_rules_hold(changed, labels, texts, frozenset())

    rank, count, total = window("r"), window("k"), window("s")
    assert count.frame is not None and total.frame is not None
    sliding = dataclasses.replace(
        total.frame, unit="rows", start=("offset_preceding", 1)
    )
    assert holds("s", total)
    assert holds("k", dataclasses.replace(count, frame=sliding))
    assert not holds("s", dataclasses.replace(total, frame=sliding))
    # `count()` with no key keeps the default frame (D78.16).
    whole = dataclasses.replace(window("c"), partition_by=())
    assert holds("c", whole)
    assert not holds("c", dataclasses.replace(whole, frame=sliding))
    # A window reads a column, never arithmetic.
    assert total.argument is not None
    negative = adapter_sql.SQLiteNegative(total.argument, None)
    assert not holds("s", dataclasses.replace(total, argument=negative))
    assert not holds("r", dataclasses.replace(rank, frame=count.frame))
    (partition,) = rank.partition_by
    unbound = dataclasses.replace(partition, collate=False)
    assert not holds("r", dataclasses.replace(rank, partition_by=(unbound,)))
    key = adapter_sql.SQLiteKey(adapter_sql.SQLiteColumn(0, None), False, None, None)
    assert not holds("r", rank, group_by=(key,))
    # A window reads one source, never JOINed rows.
    on = adapter_sql.SQLiteComparison(
        "=",
        adapter_sql.SQLiteColumn(0, None, 1),
        adapter_sql.SQLiteColumn(0, None, 0),
        False,
        None,
    )
    join = adapter_sql.SQLiteJoin("INNER", ast.table, ast.columns, on, None, None)
    assert holds("r", rank, joins=())
    assert not holds("r", rank, joins=(join,))
    # An aggregate rendered after every window.
    assert not holds("t", adapter_sql.SQLiteAggregate("count", None, False, None))


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
            ("PIE-B1004", "int_arithmetic_range_proof_missing"),
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
        return adapter_sql.ast_rules_hold(
            changed, labels, frozenset({(0, 2)}), frozenset()
        )

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


# S13a: INNER and LEFT JOINs of sqlite.table sources (T3 b).
JOINED_HEADER = (
    sqlite.JOINED_HEADER
    + """
query recent:
    from orders
    select:
        id
"""
)
joined_contract = sqlite.joined_contract


LEFT_JOIN = """query result:
    from orders
    let c = customers
    left join c on orders.id == c.id and orders.note == c.name
    where c.vip is None or c.vip
    select:
        orders.id
        c.name
    order by:
        c.name desc
    limit 4
"""
LEFT_JOIN_SQL = (
    "SELECT `s0`.`id` AS `id`, `s1`.`name` AS `name`"
    " FROM `main`.`orders` AS `s0` LEFT JOIN `main`.`customers` AS `s1`"
    " ON (`s0`.`id` = `s1`.`id`) AND (`s0`.`note` COLLATE BINARY = `s1`.`name`)"
    " WHERE (`s1`.`vip` IS NULL) OR `s1`.`vip`"
    " ORDER BY `s1`.`name` COLLATE BINARY DESC NULLS FIRST LIMIT 4"
)
GROUPED_JOIN = """query result:
    from orders
    let c = customers
    inner join c on c.id == orders.id
    where orders.ok == c.vip
    group by:
        c.name
    select:
        name = c.name
        n = count()
        a = avg(orders.amount)
        hi = max(c.rate)
    having n > 1
    order by:
        n desc
        name
"""
GROUPED_JOIN_SQL = (
    "SELECT `s1`.`name` AS `name`, COUNT(*) AS `n`,"
    " AVG(CAST(`s0`.`amount` AS REAL)) AS `a`, MAX(`s1`.`rate`) AS `hi`"
    " FROM `main`.`orders` AS `s0` INNER JOIN `main`.`customers` AS `s1`"
    " ON `s1`.`id` = `s0`.`id` WHERE `s0`.`ok` = `s1`.`vip`"
    " GROUP BY `s1`.`name` COLLATE BINARY HAVING COUNT(*) > 1"
    " ORDER BY COUNT(*) DESC NULLS FIRST, `s1`.`name` COLLATE BINARY ASC NULLS LAST"
)
# A self-join and a third input: each input has its own alias, in input order.
CHAINED_JOIN = """query result:
    from orders
    let p = orders
    let c = customers
    inner join p on orders.id == p.amount
    left join c on c.id == p.id and c.vip == p.ok
    select:
        orders.id
        pid = p.id
        c.name
"""
CHAINED_JOIN_SQL = (
    "SELECT `s0`.`id` AS `id`, `s1`.`id` AS `pid`, `s2`.`name` AS `name`"
    " FROM `main`.`orders` AS `s0` INNER JOIN `main`.`orders` AS `s1`"
    " ON `s0`.`id` = `s1`.`amount` LEFT JOIN `main`.`customers` AS `s2`"
    " ON (`s2`.`id` = `s1`.`id`) AND (`s2`.`vip` = `s1`.`ok`)"
)


@pytest.mark.parametrize(
    ("body", "sql"),
    [
        (LEFT_JOIN, LEFT_JOIN_SQL),
        (GROUPED_JOIN, GROUPED_JOIN_SQL),
        (CHAINED_JOIN, CHAINED_JOIN_SQL),
    ],
)
def test_joins_emit_their_sql(tmp_path: Path, body: str, sql: str) -> None:
    status, document = emit(tmp_path, body, joined_contract(), JOINED_HEADER)
    assert (status, document["format"], document["sql"]) == (
        "VERIFIED",
        "pietto.sql-emission.v1",
        sql,
    )
    ranges = document["ranges"]
    assert [r["start"] for r in ranges] == [0] + [r["end"] for r in ranges[:-1]]
    assert ranges[-1]["end"] == len(sql.encode("utf-8"))
    joins = [r for r in ranges if r["role"] == "join"]
    assert [r["subject"]["kind"] for r in joins] == ["join"] * sql.count(" JOIN ")


def test_joined_columns_name_their_input(tmp_path: Path) -> None:
    status, document = emit(tmp_path, LEFT_JOIN, joined_contract(), JOINED_HEADER)
    assert status == "VERIFIED"
    columns = {c["label"]: c for c in document["columns"]}
    # A LEFT JOIN's right field is nullable in the result, whatever its
    # contract says; each column names the JOIN input port it reads.
    assert columns["id"]["representation"] == sqlite.REPRESENTATIONS["Int"] | {
        "nullable": False
    }
    assert columns["name"]["representation"] == sqlite.REPRESENTATIONS["Text"] | {
        "nullable": True
    }
    assert [
        (
            c["correspondence"]["source"]["name"],
            c["correspondence"]["field"],
            c["correspondence"]["join_port"]["kind"],
            "input_port" in c["correspondence"],
        )
        for c in document["columns"]
    ] == [("orders", 0, "join_port", False), ("customers", 1, "join_port", False)]
    status, document = emit(
        tmp_path / "g", GROUPED_JOIN, joined_contract(), JOINED_HEADER
    )
    columns = {c["label"]: c for c in document["columns"]}
    assert columns["name"]["correspondence"]["group_key"]["kind"] == "group_key"
    assert columns["hi"]["representation"] == sqlite.REPRESENTATIONS["Float"] | {
        "nullable": True
    }
    # A comparison of a LEFT JOIN's right field is NULL on a left row that
    # matches nothing, and so is a `not` or an `and` of one.
    body = LEFT_JOIN.split("    where")[0] + (
        "    select:\n        orders.id\n        e = c.id == orders.id\n"
        "        nt = not (c.rate > 0.0)\n        an = c.id == 1 and orders.ok\n"
    )
    status, document = emit(tmp_path / "e", body, joined_contract(), JOINED_HEADER)
    assert [
        (c["label"], c["nullable"], c["representation"]["nullable"])
        for c in document["columns"]
    ] == [
        ("id", False, False),
        ("e", True, True),
        ("nt", True, True),
        ("an", True, True),
    ]


def _join(on: str, kind: str = "inner", extra: str = "") -> str:
    return (
        "query result:\n    from orders\n    let c = customers\n"
        f"    {kind} join c on {on}\n{extra}    select:\n        orders.id\n"
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (_join("orders.id == c.id", "right"), [(5.1, 27)]),
        (_join("orders.id == c.id", "full"), [(5.1, 27)]),
        (_join("orders.id > c.id"), [(5.1, 27)]),
        (_join("orders.price == c.rate"), [(5.1, 27)]),
        (_join("orders.id == c.id or orders.note == c.name"), [(5.1, 27)]),
        (_join("orders.id == c.id and orders.amount == orders.id"), [(5.1, 27)]),
        (_join("orders.id == c.id and c.id == 1"), [(5.1, 27)]),
        (
            "query result:\n    from orders\n    let c = customers\n"
            "    cross join c\n    select:\n        orders.id\n",
            [(5.1, 27)],
        ),
        (
            # A JOIN to a query: rule 5 at the JOIN, as in tier 1.
            "query result:\n    from orders\n    let r = recent\n"
            "    inner join r on orders.id == r.id\n    select:\n        orders.id\n",
            [(5, 27), (5.1, 27)],
        ),
        (
            # After an admitted JOIN, both rules name the JOIN to a query.
            "query result:\n    from orders\n    let c = customers\n"
            "    let r = recent\n    inner join c on orders.id == c.id\n"
            "    inner join r on orders.id == r.id\n    select:\n        orders.id\n"
            "    order by:\n        c.name\n",
            [(5, 29), (5.1, 29)],
        ),
        (
            # Beside a JOIN to a query, rules 9-13 and 35 are not checked:
            # not the mixed-sign sum after it, nor a source's fields before
            # or after it, nor arithmetic.
            "query result:\n    from orders\n    let c = customers\n"
            "    let r = folks\n    inner join c on orders.id == c.id\n"
            "    inner join r on orders.id == r.id\n    select:\n"
            "        s = sum(orders.amount)\n"
            "\nquery folks:\n    from customers\n    select:\n        id\n",
            [(5, 29), (5.1, 29)],
        ),
        (
            "query result:\n    from orders\n    let c = customers\n"
            "    let r = folks\n    inner join r on orders.id == r.id\n"
            "    inner join c on orders.id == c.id\n    group by:\n        c.name\n"
            "    select:\n        name = c.name\n        m = max(c.rate)\n"
            "\nquery folks:\n    from customers\n    select:\n        id\n",
            [(5, 28), (5.1, 28)],
        ),
        (
            "query result:\n    from orders\n    let c = customers\n"
            "    let r = folks\n    inner join r on orders.id == r.id\n"
            "    inner join c on orders.id == c.id\n"
            "    where orders.amount + 1 > 2\n    select:\n        c.name\n"
            "    order by:\n        c.name\n"
            "\nquery folks:\n    from customers\n    select:\n        id\n",
            [(5, 28), (5.1, 28)],
        ),
        (
            # A relationship's call, which the plan writes out as `==`.
            _join("OC(orders, c)", "left")
            + "\nrelationship OC(o: Order, c: Customer): o.id == c.id\n",
            [(5.1, 27)],
        ),
        (
            # An any() read is no JOIN: it stays refused as in tier 1.
            "query result:\n    from orders\n"
            "    where any(c.id == orders.id for c in customers)\n"
            "    select:\n        id\n",
            [(5, 24), (6, 17), (9, 26)],
        ),
        # Refused for another reason beside an admitted JOIN (77-2): the
        # first site of rule 5 is `distinct`, and of rule 9b the sum, whose
        # bounds the full `int_range` of `amount` leaves unproved.
        (
            _join("orders.id == c.id").replace("select:", "select distinct:"),
            [(5, 28)],
        ),
        (
            _join("orders.id == c.id", extra="    where orders.amount + 1 > 2\n"),
            [(9.2, 28)],
        ),
        # Rule 5 refuses a window over joined rows. Rule 5b also reports
        # this ranking window, to which the plan gives modifiers over a
        # JOIN; a `count()` window there has rule 5 alone.
        (
            _join("orders.id == c.id").replace(
                "orders.id\n", "w = row_number() window(order by orders.id)\n"
            ),
            [(5, 24), (5.2, 24)],
        ),
    ],
)
def test_join_refusals_at_their_first_site(
    tmp_path: Path, body: str, expected: list[tuple[float, int]]
) -> None:
    status, document = emit(tmp_path, body, joined_contract(), JOINED_HEADER)
    assert status == "BLOCKED", document
    rules = {
        "sqlite_relation_shape_not_admitted": 5,
        "sqlite_source_count_not_admitted": 6,
        "sqlite_join_not_admitted": 5.1,
        "sqlite_window_not_admitted": 5.2,
        "sqlite_expression_not_admitted": 9,
        "int_arithmetic_range_proof_missing": 9.2,
        "sqlite_aggregate_not_admitted": 10,
        "sqlite_group_key_not_admitted": 12,
        "sqlite_order_not_admitted": 13,
        "sum_int_aggregate_range_proof_missing": 35,
    }
    assert [
        (rules[b["subject"]["detail"]], b["location"]["line"])
        for b in document["blockers"]
    ] == expected
    assert [b["code"] for b in document["blockers"]] == [
        "PIE-B1004" if rule in (9.2, 35) else "PIE-B1003" for rule, _line in expected
    ]


def test_a_joined_source_passes_the_source_rules(tmp_path: Path) -> None:
    # Rules 23-35 hold for each JOIN input's source: one without a contract
    # entry, of another family, or with a mixed-sign sum.
    status, document = emit(
        tmp_path / "a", GROUPED_JOIN, joined_contract(customers=False), JOINED_HEADER
    )
    assert details(document) == [("PIE-B1001", "source_mapping_missing")]
    header = JOINED_HEADER.replace(
        'sqlite.table("customers")', 'postgres.table("customers")'
    )
    status, document = emit(tmp_path / "b", GROUPED_JOIN, joined_contract(), header)
    assert ("PIE-B1001", "source_family_mismatch") in details(document)
    body = GROUPED_JOIN.replace("a = avg(orders.amount)", "a = sum(orders.amount)")
    status, document = emit(tmp_path / "c", body, joined_contract(), JOINED_HEADER)
    assert details(document) == [("PIE-B1004", "sum_int_aggregate_range_proof_missing")]
    contract = joined_contract()
    contract["sources"][1]["fields"][1]["representation"]["domain"]["collation"] = (
        "NOCASE"
    )
    status, document = emit(tmp_path / "d", LEFT_JOIN, contract, JOINED_HEADER)
    assert details(document) == [("PIE-B1002", "physical_storage_or_domain_mismatch")]


@pytest.mark.parametrize(
    ("narrowed", "select", "expected"),
    [
        (0, "v = c.id + 1", [("PIE-B1004", "int_arithmetic_range_proof_missing")]),
        (1, "v = c.id + 1", []),
        (0, "s = sum(c.id)", [("PIE-B1004", "sum_int_aggregate_range_proof_missing")]),
        (1, "s = sum(c.id)", []),
    ],
)
def test_joined_arithmetic_reads_its_own_input_s_int_range(
    tmp_path: Path, narrowed: int, select: str, expected: list[tuple[str, str]]
) -> None:
    """Rules 9b and 35 read the `int_range` of the input whose field they
    read: `id` lies from 0 to 100 in one source's contract only, and `c.id`
    is proved by `customers`' alone."""
    document = joined_contract()
    domain = document["sources"][narrowed]["fields"][0]["representation"]["domain"]
    domain.update(min="0", max="100")
    # Both sides keyed, so a `sum` reads no row that the JOIN repeats.
    header = JOINED_HEADER.replace(
        "    price: Float\n", "    price: Float\n    order_key = unique(id)\n", 1
    )
    body = _join("orders.id == c.id").replace("orders.id\n", f"{select}\n")
    status, emitted = emit(tmp_path, body, document, header)
    if expected:
        assert (status, details(emitted)) == ("BLOCKED", expected)
    else:
        assert status == "VERIFIED", emitted


def test_the_verifier_refuses_a_changed_join(tmp_path: Path) -> None:
    root = sqlite.write(
        tmp_path / "project", LEFT_JOIN, joined_contract(), JOINED_HEADER
    )
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
    ast = outcome.artifact.ast
    labels = tuple(result.label for result in ast.results)
    (join,) = ast.joins
    assert type(join.on) is adapter_sql.SQLiteLogical
    equality = join.on.left
    assert type(equality) is adapter_sql.SQLiteComparison

    def holds(**change: object) -> bool:
        changed = dataclasses.replace(ast, joins=(dataclasses.replace(join, **change),))
        texts = frozenset({(0, 2), (1, 1)})
        return adapter_sql.ast_rules_hold(changed, labels, texts, frozenset())

    assert holds()
    assert not holds(kind="RIGHT")
    assert not holds(on=dataclasses.replace(equality, operator="<"))
    assert not holds(on=dataclasses.replace(equality, right=equality.left))
    for column in (
        adapter_sql.SQLiteColumn(0, None, 2),
        adapter_sql.SQLiteColumn(4, None, 1),
    ):
        result = dataclasses.replace(ast.results[0], value=column)
        assert not adapter_sql.ast_rules_hold(
            dataclasses.replace(ast, results=(result, *ast.results[1:])),
            labels,
            frozenset({(0, 2), (1, 1)}),
            frozenset(),
        )


def test_a_join_needs_the_operator_environment(tmp_path: Path) -> None:
    document = joined_contract()
    document["environment"] = [
        e for e in document["environment"] if e["key"] != "operator_environment"
    ]
    status, found = emit(tmp_path, CHAINED_JOIN, document, JOINED_HEADER)
    assert details(found) == [("PIE-B1004", "operator_environment_declaration_missing")]


@pytest.mark.parametrize("joins", [63, 64])
def test_a_statement_joins_at_most_64_inputs(tmp_path: Path, joins: int) -> None:
    body = "query result:\n    from orders\n"
    body += "".join(f"    let p{n} = orders\n" for n in range(joins))
    body += "".join(
        f"    inner join p{n} on orders.id == p{n}.id\n" for n in range(joins)
    )
    body += "    select:\n        orders.id\n"
    status, document = emit(tmp_path, body, joined_contract(), JOINED_HEADER)
    if joins < 64:
        assert status == "VERIFIED"
    else:
        assert details(document) == [("PIE-B1007", "generated_structure_limit")]
