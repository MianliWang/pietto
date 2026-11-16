"""DuckDB emission through its independent adapter (AD78.03).

The expected SQL bytes, blockers and suggestions are those of
docs/spec/duckdb-arrow-route-v1.md, written before the runs. Every document
is read through `compile_sql`, which returns the bytes of `pietto emit-sql
--project ... --format json`; tampered artifacts are labelled forgeries.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from _pietto_repo_facts import REPOSITORY_FACTS
from _pietto_sql_duckdb import (
    FIELDS,
    GROUPED,
    GROUPED_SQL,
    HEADER,
    INT,
    ORDERED,
    ORDERED_SQL,
    PROJECTION,
    PROJECTION_SQL,
    contract,
    filtered,
    source_entry,
    statement,
    write,
)
from pietto import execution
from pietto._project import project_duckdb_emission as adapter
from pietto._project import project_duckdb_sql as duckdb_sql
from pietto._project import project_public_execution
from pietto._project import project_sql_emission_cli as emission_cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
    with_project_single_match_requests,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_single_match import ProjectSingleMatchRequest
from pietto._project.project_sql_plan import build_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto.compiler import compile_sql

REPO_ROOT = Path(__file__).resolve().parents[1]


def selected(body: str) -> dict[str, str]:
    kind = "query" if body.startswith("query") else "table"
    return {"module": "main.pietto", "kind": kind, "name": "result"}


def emit(
    root: Path, body: str, dialect: str = "duckdb", policy: str = "preserve"
) -> tuple[str, dict[str, Any]]:
    emission = compile_sql(
        root,
        **selected(body),
        dialect=dialect,
        emission_contract="contract.json",
        literal_policy=policy,
    )
    return emission.status, json.loads(emission.document)


def blockers(document: dict[str, Any]) -> list[tuple[str, str]]:
    return [(b["code"], b["subject"]["detail"]) for b in document["blockers"]]


OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


@pytest.mark.parametrize("operator", OPERATORS)
def test_a_filtered_query_is_one_select_over_the_registered_capture(
    tmp_path: Path, operator: str
) -> None:
    body = filtered(operator)
    status, document = emit(write(tmp_path / "p", body, contract()), body)
    assert status == "VERIFIED" and document["format"] == "pietto.sql-emission.v2"
    assert document["sql"] == (
        'SELECT "c0" AS "id", "c4" AS "price" FROM temp.main."pietto_arrow_0"'
        f' WHERE "c1" {OPERATORS[operator]} CAST($1 AS BIGINT)'
    )
    assert document["target"]["family"] == "duckdb"
    assert document["target"]["release"] == "2.0.0"
    assert document["fixed_values"] == [] and document["binding_obligations"] == []
    (use,) = document["parameter_uses"]
    assert document["sql"][use["range"]["start"] : use["range"]["end"]] == "$1"
    assert (use["owner"], use["server_index"], use["physical_type"]) == (
        {"kind": "parameter", "parameter": 0},
        1,
        "duckdb_bigint",
    )
    (parameter,) = document["parameters"]
    assert (parameter["name"], parameter["tag"], parameter["nullable"]) == (
        "min_amount",
        "Int",
        False,
    )
    columns = [
        (
            c["label"],
            c["logical_type"]["name"],
            c["nullable"],
            c["correspondence"]["field"],
        )
        for c in document["columns"]
    ]
    assert columns == [("id", "Int", False, 0), ("price", "Float", False, 4)]
    # The ranges cover the statement byte for byte, in order.
    ends = [(r["start"], r["end"]) for r in document["ranges"]]
    assert ends[0][0] == 0 and ends[-1][1] == len(document["sql"].encode())
    assert all(a[1] == b[0] for a, b in zip(ends, ends[1:]))


def test_a_projection_names_only_pietto_owned_identifiers(tmp_path: Path) -> None:
    body = PROJECTION.replace("        note\n", "        label = note\n")
    key = source_entry()
    key["relation"]["name"] = "Odd key/é"
    for field in key["fields"]:
        field["column"] = "Caller " + field["column"]
    header = HEADER.replace('duckdb.arrow("orders")', 'duckdb.arrow("Odd key/é")')
    status, document = emit(write(tmp_path / "p", body, contract(key), header), body)
    assert (status, document["format"]) == ("VERIFIED", "pietto.sql-emission.v1")
    assert document["sql"] == PROJECTION_SQL.replace('"note"', '"label"')
    assert "parameters" not in document and document["parameter_uses"] == []
    assert [c["nullable"] for c in document["columns"]] == [False, True]


def _grouped(select: str, rest: str = "", head: str = "table result:") -> str:
    """A statement over `orders` grouped by `note`, selecting it and `select`."""
    return (
        f"{head}\n    from orders\n    group by note\n    select:\n        note\n"
        f"        {select}\n{rest}"
    )


GROUPED_FORMS = {
    "global": (
        "table result:\n    from orders\n    select:\n        n = count()\n"
        "        top = max(price)\n",
        'SELECT count(*) AS "n", max("c4") AS "top" FROM temp.main."pietto_arrow_0"',
    ),
    "float_key": (
        "table result:\n    from orders\n    group by price\n    select:\n"
        "        price\n        n = count(note)\n",
        'SELECT "c4" AS "price", count("c2") AS "n" FROM temp.main."pietto_arrow_0"'
        ' GROUP BY "pietto_arrow_0"."c4"',
    ),
    "where": (
        filtered(">=")
        .replace("    select:", "    group by note\n    select:")
        .replace("        id\n        price\n", "        note\n        n = count()\n"),
        'SELECT "c2" AS "note", count(*) AS "n" FROM temp.main."pietto_arrow_0"'
        ' WHERE "c1" >= CAST($1 AS BIGINT) GROUP BY "pietto_arrow_0"."c2"',
    ),
    "having_count": (
        _grouped("n = count()", "    having n > p\n", "query result(p: Int):"),
        'SELECT "c2" AS "note", count(*) AS "n" FROM temp.main."pietto_arrow_0"'
        ' GROUP BY "pietto_arrow_0"."c2" HAVING count(*) > CAST($1 AS BIGINT)',
    ),
    "having_key": (
        "query result(p: Int):\n    from orders\n    group by id\n    select:\n"
        "        c0 = id\n        s = sum(amount)\n    having c0 != p\n",
        'SELECT "c0" AS "c0", CAST(sum("c1") AS BIGINT) AS "s"'
        ' FROM temp.main."pietto_arrow_0" GROUP BY "pietto_arrow_0"."c0"'
        ' HAVING "pietto_arrow_0"."c0" <> CAST($1 AS BIGINT)',
    ),
}


@pytest.mark.parametrize("case", GROUPED_FORMS)
def test_grouped_and_global_aggregates_read_qualified_names(
    tmp_path: Path, case: str
) -> None:
    body, sql = GROUPED_FORMS[case]
    status, document = emit(write(tmp_path / "p", body, contract()), body)
    assert (status, document["sql"]) == ("VERIFIED", sql)
    ends = [(r["start"], r["end"]) for r in document["ranges"]]
    assert ends[0][0] == 0 and ends[-1][1] == len(sql.encode())
    assert all(a[1] == b[0] for a, b in zip(ends, ends[1:]))


def test_a_grouped_query_documents_each_key_and_aggregate(tmp_path: Path) -> None:
    root = write(tmp_path / "p", GROUPED, contract())
    status, document = emit(root, GROUPED)
    assert (status, document["sql"]) == ("VERIFIED", GROUPED_SQL)
    assert document["format"] == "pietto.sql-emission.v2"
    columns = [
        (
            c["label"],
            c["logical_type"]["name"],
            c["nullable"],
            c["correspondence"]["field"],
            c["correspondence"].get("function"),
            c["representation"]["storage"]["kind"],
            c["representation"]["domain"].get("min"),
        )
        for c in document["columns"]
    ]
    least = str(-(2**63))
    assert columns == [
        ("note", "Text", True, 2, None, "arrow_string", None),
        ("ok", "Bool", False, 3, None, "arrow_bool", None),
        ("n", "Int", False, None, "count", "arrow_int64", "0"),
        ("filled", "Int", False, 2, "count", "arrow_int64", "0"),
        ("c1", "Int", True, 1, "sum", "arrow_int64", least),
        ("low", "Float", True, 4, "min", "arrow_float64", None),
        ("high", "Int", True, 0, "max", "arrow_int64", least),
    ]
    assert all(
        c["representation"]["nullable"] is c["nullable"] for c in document["columns"]
    )
    (use,) = document["parameter_uses"]
    assert GROUPED_SQL.encode()[use["range"]["start"] : use["range"]["end"]] == b"$1"
    (parameter,) = document["parameters"]
    (read,) = parameter["reads"]
    (placeholder,) = (r for r in document["ranges"] if r["kind"] == "parameter")
    assert read == placeholder["subject"] and read["kind"] == "expression"
    query = execution.compile_query(
        root, **selected(GROUPED), dialect="duckdb", emission_contract="contract.json"
    )
    assert adapter.execution_facts(query._template).result == (
        ("note", "Text", True),
        ("ok", "Bool", False),
        ("n", "Int", False),
        ("filled", "Int", False),
        ("c1", "Int", True),
        ("low", "Float", True),
        ("high", "Int", True),
    )
    # Rule 16 counts the AST's nodes from the plan: the statement and its
    # relation, a value and a label per column, the read in each of four
    # aggregates, a read per key and the having's comparison, value and
    # placeholder.
    for nodes, expected in ((25, "VERIFIED"), (24, "BLOCKED")):
        limited = contract()
        limited["environment"].append(statement("resource_limits", {"nodes": nodes}))
        status, emitted = emit(write(tmp_path / str(nodes), GROUPED, limited), GROUPED)
        assert status == expected
    assert blockers(emitted) == [("PIE-B1007", "generated_structure_limit")]


ORDERED_FORMS = {
    "keys_and_limit": (
        PROJECTION + "    order by:\n        id desc\n        amount\n    limit 3\n",
        PROJECTION_SQL + ' ORDER BY "pietto_arrow_0"."c0" DESC NULLS FIRST,'
        ' "pietto_arrow_0"."c1" ASC NULLS LAST LIMIT 3',
    ),
    "limit_zero": (PROJECTION + "    limit 0\n", PROJECTION_SQL + " LIMIT 0"),
    "largest_limit": (
        PROJECTION + f"    limit {2**63 - 1}\n",
        PROJECTION_SQL + f" LIMIT {2**63 - 1}",
    ),
    # A bare "c1" in ORDER BY would find the label before the column.
    "field_named_like_a_label": (
        PROJECTION.replace("        note\n", "        c1 = note\n")
        + "    order by:\n        amount\n",
        PROJECTION_SQL.replace('"note"', '"c1"')
        + ' ORDER BY "pietto_arrow_0"."c1" ASC NULLS LAST',
    ),
    "where": (
        filtered(">=") + "    order by:\n        price desc\n    limit 5\n",
        'SELECT "c0" AS "id", "c4" AS "price" FROM temp.main."pietto_arrow_0"'
        ' WHERE "c1" >= CAST($1 AS BIGINT)'
        ' ORDER BY "pietto_arrow_0"."c4" DESC NULLS FIRST LIMIT 5',
    ),
    "count_key": (
        _grouped("n = count()", "    order by:\n        n desc\n"),
        'SELECT "c2" AS "note", count(*) AS "n" FROM temp.main."pietto_arrow_0"'
        ' GROUP BY "pietto_arrow_0"."c2" ORDER BY count(*) DESC NULLS FIRST',
    ),
    "grouped": (ORDERED, ORDERED_SQL),
}


@pytest.mark.parametrize("case", ORDERED_FORMS)
def test_order_keys_restate_their_values_with_nulls_clauses(
    tmp_path: Path, case: str
) -> None:
    body, sql = ORDERED_FORMS[case]
    status, document = emit(write(tmp_path / "p", body, contract()), body)
    assert (status, document["sql"]) == ("VERIFIED", sql)
    ends = [(r["start"], r["end"]) for r in document["ranges"]]
    assert ends[0][0] == 0 and ends[-1][1] == len(sql.encode())
    assert all(a[1] == b[0] for a, b in zip(ends, ends[1:]))
    uses = [
        sql.encode()[u["range"]["start"] : u["range"]["end"]]
        for u in document["parameter_uses"]
    ]
    assert uses == ([b"$1"] if "$1" in sql else [])


def test_order_keys_and_the_limit_count_toward_the_nodes(tmp_path: Path) -> None:
    """GROUPED's 25 nodes, then a key and its value per order key and the
    limit."""
    for nodes, expected in ((32, "VERIFIED"), (31, "BLOCKED")):
        limited = contract()
        limited["environment"].append(statement("resource_limits", {"nodes": nodes}))
        status, emitted = emit(write(tmp_path / str(nodes), ORDERED, limited), ORDERED)
        assert status == expected
    assert blockers(emitted) == [("PIE-B1007", "generated_structure_limit")]


def test_order_refusals_report_their_sites(tmp_path: Path) -> None:
    """Rule 8a at the first computed key, with the text the owner agreed to;
    rule 5 alone at the `order by` whose key names a renamed or computed
    output, for which the plan is unavailable."""
    computed = (
        PROJECTION + "    order by:\n        id\n        -amount\n        amount + 1\n"
    )
    renamed = (
        PROJECTION.replace("        note\n", "        label = note\n")
        + "    order by:\n        label\n"
    )
    output = (
        PROJECTION.replace("        note\n", "        more = amount + 1\n")
        + "    order by:\n        more\n"
    )
    for name, body, detail, site in (
        ("computed", computed, "duckdb_order_not_admitted", (17, 9)),
        ("renamed", renamed, "duckdb_relation_shape_not_admitted", (15, 5)),
        ("output", output, "duckdb_relation_shape_not_admitted", (15, 5)),
    ):
        status, document = emit(write(tmp_path / name, body, contract()), body)
        assert (status, blockers(document)) == ("BLOCKED", [("PIE-B1003", detail)])
        (blocker,) = document["blockers"]
        location = blocker["location"]
        assert (location["line"], location["column"]) == site
    assert adapter.suggestion("PIE-B1003", "duckdb_order_not_admitted") == (
        "order by source fields or selected outputs, such as order by total"
        " desc; computed keys are not available on DuckDB"
    )


SHAPES = {
    # The key reads a selected output, which rule 7 refuses.
    "computed_output_order_key": (
        _grouped("t = sum(amount) + 1", "    order by:\n        t\n"),
        [("PIE-B1003", "duckdb_projection_not_admitted")],
    ),
    "avg": (
        _grouped("mean = avg(amount)"),
        [("PIE-B1003", "duckdb_aggregate_not_admitted")],
    ),
    "sum_of_a_float": (
        _grouped("s = sum(price)"),
        [("PIE-B1003", "duckdb_aggregate_not_admitted")],
    ),
    "computed_argument": (
        _grouped("n = count(amount + 1)"),
        [("PIE-B1003", "duckdb_aggregate_not_admitted")],
    ),
    "count_distinct": (
        _grouped("n = count_distinct(id)"),
        [("PIE-B1003", "duckdb_aggregate_not_admitted")],
    ),
    "computed_key": (
        "table result:\n    from orders\n    let bucket = amount * 2\n"
        "    group by bucket\n    select:\n        bucket\n        n = count()\n",
        [
            ("PIE-B1003", "duckdb_relation_shape_not_admitted"),
            ("PIE-B1003", "duckdb_projection_not_admitted"),
            ("PIE-B1003", "duckdb_grouping_not_admitted"),
        ],
    ),
    "computed_output": (
        _grouped("t = sum(amount) + 1"),
        [("PIE-B1003", "duckdb_projection_not_admitted")],
    ),
    "having_literal": (
        _grouped("n = count()", "    having n > 3\n"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "having_float": (
        _grouped("low = min(price)", "    having low > p\n", "query result(p: Float):"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "where_and_having": (
        _grouped("n = count()", "    having n > p\n", "query result(p: Int):").replace(
            "    group by", "    where amount > p\n    group by"
        ),
        [("PIE-B1003", "duckdb_parameter_not_admitted")],
    ),
    "derived_source": (
        PROJECTION.replace("table result", "table base")
        + "table result:\n    from base\n    select:\n        id\n",
        [("PIE-B1003", "duckdb_relation_shape_not_admitted")],
    ),
    "computed": (
        PROJECTION.replace("        note\n", "        more = amount + 1\n"),
        [("PIE-B1003", "duckdb_projection_not_admitted")],
    ),
    "literal_filter": (
        PROJECTION.replace("    select:", "    where amount > 3\n    select:"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "parameter_on_the_left": (
        filtered(">").replace("amount > min_amount", "min_amount < amount"),
        [("PIE-B1003", "duckdb_filter_not_admitted")],
    ),
    "bool_comparison": (
        filtered("==", "flag: Bool").replace("amount == min_amount", "ok == flag"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "nullable_parameter": (
        filtered(">=", "min_amount: Int | None"),
        [("PIE-B1003", "duckdb_parameter_not_admitted")],
    ),
    "parameter_read_twice": (
        filtered(">=") + "        echo = min_amount\n",
        [
            ("PIE-B1003", "duckdb_projection_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "unavailable_plan": (
        PROJECTION.replace("from orders", "from pending"),
        [("PIE-B1003", "duckdb_relation_shape_not_admitted")],
    ),
}


@pytest.mark.parametrize("case", SHAPES)
def test_unsupported_shapes_are_blocked_in_rule_order(
    tmp_path: Path, case: str
) -> None:
    body, expected = SHAPES[case]
    header = HEADER + "source pending: Order = duckdb.arrow(None)\n"
    status, document = emit(write(tmp_path / "p", body, contract(), header), body)
    assert (status, blockers(document)) == ("BLOCKED", expected)
    for blocker in document["blockers"]:
        assert blocker["suggestion"] == adapter.suggestion(
            blocker["code"], blocker["subject"]["detail"]
        )
        assert blocker["location"]["path"] == "main.pietto"


def _change(document: dict[str, Any], path: str, value: object) -> dict[str, Any]:
    *parents, last = path.split("/")
    node: Any = document
    for part in parents:
        node = node[int(part) if part.isdigit() else part]
    key: Any = int(last) if last.isdigit() else last
    if value is _DROP:
        del node[key]
    elif type(node) is list and key == len(node):
        node.append(value)
    else:
        node[key] = value
    return document


_DROP = object()
FIELD0 = "sources/0/fields/0/representation"
CONTRACTS = {
    "release": (
        "target/release",
        "1.4.0",
        [("PIE-B1003", "target_release_not_reviewed")],
    ),
    "identifier_case": (
        "environment/3",
        statement("identifier_case", "quoted_exact"),
        [("PIE-B1003", "premise_not_admitted_on_target")],
    ),
    "conflicting_premises": (
        "environment/3",
        statement("client_encoding", "utf8mb4"),
        [
            ("PIE-B1005", "inconsistent_declared_scope"),
            ("PIE-B1005", "client_encoding_mismatch"),
        ],
    ),
    "operator_environment_missing": (
        "environment/1",
        _DROP,
        [("PIE-B1004", "operator_environment_declaration_missing")],
    ),
    "operator_environment_mismatch": (
        "environment/1/value",
        "session_defined",
        [("PIE-B1005", "operator_environment_declaration_mismatch")],
    ),
    "parameter_protocol_missing": (
        "environment/2",
        _DROP,
        [("PIE-B1004", "parameter_protocol_declaration_missing")],
    ),
    "parameter_protocol_mismatch": (
        "environment/2/value",
        "postgres_extended",
        [("PIE-B1005", "parameter_protocol_declaration_mismatch")],
    ),
    "parameter_limit": (
        "environment/3",
        statement("resource_limits", {"parameters": 0}),
        [("PIE-B1007", "parameter_occurrence_limit")],
    ),
    "column_limit": (
        "environment/3",
        statement("resource_limits", {"columns": 2}),
        [("PIE-B1007", "generated_structure_limit")],
    ),
    "mapping_missing": ("sources", [], [("PIE-B1001", "source_mapping_missing")]),
    "namespace": (
        "sources/0/relation/namespace",
        "public",
        [("PIE-B1001", "source_identifier_unrepresentable")],
    ),
    "key_case": (
        "sources/0/relation/name",
        "Orders",
        [("PIE-B1001", "duckdb_arrow_key_mismatch")],
    ),
    "row_domain": (
        "sources/0/premises/0",
        _DROP,
        [("PIE-B1001", "row_domain_matches_declaration_required")],
    ),
    "read_only": (
        "sources/0/premises/1/value",
        False,
        [("PIE-B1001", "read_only_object_declaration_required")],
    ),
    "client_encoding_missing": (
        "environment/0",
        _DROP,
        [("PIE-B1004", "client_encoding_declaration_missing")],
    ),
    "nullability": (
        "sources/0/fields/2/representation/nullable",
        False,
        [("PIE-B1002", "nullability_mismatch")],
    ),
    "unknown_nullability": (
        FIELD0 + "/nullable",
        "unknown",
        [("PIE-B1002", "nullability_mismatch")],
    ),
    "storage": (
        FIELD0 + "/storage/kind",
        "arrow_string",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    ),
    "int_domain": (
        FIELD0 + "/domain/min",
        str(-(2**63) - 1),
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    ),
    "collation": (
        "sources/0/fields/2/representation/domain/collation",
        "und",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    ),
    "field_premise": (
        "sources/0/premises/2",
        {"key": "collation", "scope": "source", "value": "und"},
        [("PIE-B1005", "field_domain_premise_mismatch")],
    ),
}


@pytest.mark.parametrize("case", CONTRACTS)
def test_contract_values_are_blocked_in_rule_order(tmp_path: Path, case: str) -> None:
    path, value, expected = CONTRACTS[case]
    body = filtered(">=")
    document = _change(contract(), path, value)
    status, emitted = emit(write(tmp_path / "p", body, document), body)
    assert (status, blockers(emitted)) == ("BLOCKED", expected)
    for blocker in emitted["blockers"]:
        assert blocker["suggestion"] == adapter.suggestion(
            blocker["code"], blocker["subject"]["detail"]
        )


def test_the_byte_limits_admit_exactly_their_bytes(tmp_path: Path) -> None:
    body = filtered(">=")

    def limited(key: str, value: int) -> tuple[str, bytes]:
        document = contract()
        document["environment"].append(statement("resource_limits", {key: value}))
        root = write(tmp_path / f"{key}-{value}", body, document)
        emission = compile_sql(
            root, **selected(body), dialect="duckdb", emission_contract="contract.json"
        )
        return emission.status, emission.document

    sql = emit(write(tmp_path / "p", body, contract()), body)[1]["sql"].encode()
    assert limited("sql_bytes", len(sql))[0] == "VERIFIED"
    status, emitted = limited("sql_bytes", len(sql) - 1)
    assert (status, blockers(json.loads(emitted))) == (
        "BLOCKED",
        [("PIE-B1007", "sql_byte_limit")],
    )
    # The document holds the limit itself; a limit of as many digits keeps
    # its size.
    status, emitted = limited("artifact_bytes", 99999)
    size = len(emitted)
    assert status == "VERIFIED" and 10000 < size < 99999
    status, emitted = limited("artifact_bytes", size)
    assert (status, len(emitted)) == ("VERIFIED", size)
    status, emitted = limited("artifact_bytes", size - 1)
    assert (status, blockers(json.loads(emitted))) == (
        "BLOCKED",
        [("PIE-B1007", "public_artifact_byte_limit")],
    )


JOIN = """table result:
    from orders
    inner join more on orders.id == more.id
    select:
        a = orders.id
"""
JOINED = [
    ("PIE-B1003", "duckdb_relation_shape_not_admitted"),
    ("PIE-B1003", "duckdb_source_count_not_admitted"),
    ("PIE-B1003", "duckdb_projection_not_admitted"),
]


def test_a_second_source_is_refused_at_its_declaration(tmp_path: Path) -> None:
    header = HEADER + 'source more: Order = duckdb.arrow("more")\n'
    document = contract(source_entry(), source_entry("more"))
    status, emitted = emit(write(tmp_path / "duckdb", JOIN, document, header), JOIN)
    assert (status, blockers(emitted)) == ("BLOCKED", JOINED)
    assert emitted["blockers"][1]["location"]["line"] == 9  # source more
    # Rule 27 of the first source is found before rules 19 and 20 of the
    # second, and listed after them.
    header = HEADER + 'source more: Order = postgres.table("more")\n'
    document = _change(contract(), "sources/0/fields/2/representation/nullable", False)
    status, emitted = emit(write(tmp_path / "postgres", JOIN, document, header), JOIN)
    assert blockers(emitted) == JOINED + [
        ("PIE-B1006", "negative_original_target_evidence"),
        ("PIE-B1001", "source_family_mismatch"),
        ("PIE-B1001", "source_mapping_missing"),
        ("PIE-B1002", "nullability_mismatch"),
    ]
    assert [b["location"]["line"] for b in emitted["blockers"][4:]] == [9, 9, 4]


@pytest.mark.parametrize("logical", ("Date", "Decimal(10, 2)"))
def test_a_field_of_another_type_is_refused_at_the_field(
    tmp_path: Path, logical: str
) -> None:
    """The field is refused although the statement does not read it."""
    header = HEADER.replace(
        "    price: Float\n", f"    price: Float\n    day: {logical}\n"
    )
    document = contract(source_entry(fields=FIELDS + (("day", "Int", False),)))
    status, emitted = emit(
        write(tmp_path / "p", PROJECTION, document, header), PROJECTION
    )
    assert (status, blockers(emitted)) == (
        "BLOCKED",
        [
            ("PIE-B1003", "duckdb_field_type_not_admitted"),
            ("PIE-B1002", "physical_storage_or_domain_mismatch"),
        ],
    )
    assert [b["location"]["line"] for b in emitted["blockers"]] == [7, 7]


@pytest.mark.parametrize(
    "changes,expected",
    (
        # Fields 0 and 2 break rule 27; the first in shape order is the site.
        (
            {"0/nullable": True, "2/nullable": False},
            [("PIE-B1002", "nullability_mismatch", 2)],
        ),
        # Rule 28 at field 0 is found before rule 27 at field 1, and listed
        # after it.
        (
            {"0/storage/kind": "arrow_string", "1/nullable": True},
            [
                ("PIE-B1002", "nullability_mismatch", 3),
                ("PIE-B1002", "physical_storage_or_domain_mismatch", 2),
            ],
        ),
    ),
)
def test_field_rules_report_their_first_field_in_rule_order(
    tmp_path: Path, changes: dict[str, object], expected: list[tuple[str, str, int]]
) -> None:
    document = contract()
    for path, value in changes.items():
        field, _, rest = path.partition("/")
        _change(document, f"sources/0/fields/{field}/representation/{rest}", value)
    status, emitted = emit(write(tmp_path / "p", PROJECTION, document), PROJECTION)
    assert status == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"])
        for b in emitted["blockers"]
    ] == expected


def test_an_unfulfilled_single_match_obligation_is_rule_18(tmp_path: Path) -> None:
    """The command registers no single-match request: only the upstream
    `with_project_single_match_requests` does, so this witness registers one
    through it, as the PostgreSQL/MySQL witness of this detail does."""
    header = HEADER + 'source more: Order = duckdb.arrow("more")\n'
    document = contract(source_entry(), source_entry("more"))
    root = write(tmp_path / "p", JOIN, document, header)
    assert blockers(emit(root, JOIN)[1]) == JOINED
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    assert type(completed) is ProjectConcreteCompletedSemanticResult
    (condition,) = completed.roots.join_conditions.entries
    completed = with_project_single_match_requests(
        completed,
        (ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use),),
    )
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    (owner,) = (o for o in ir.owners if o.definition.name == "result")
    plan = build_project_sql_plan(completed, bundle, owner)
    checked = verify_project_sql_plan(plan, completed, bundle, owner)
    outcome = adapter.emit_duckdb_sql(
        checked,
        (root / "contract.json").read_bytes(),
        emission_cli.POLICIES["preserve"],
    )
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == JOINED + [
        ("PIE-B1006", "original_enforcement_not_fulfilled")
    ]


def test_suggestions_are_the_routes_or_the_existing_texts() -> None:
    assert adapter.suggestion("PIE-B1003", "target_release_not_reviewed") == (
        'the reviewed duckdb release is "2.0.0"'
    )
    assert adapter.suggestion(
        "PIE-B1004", "parameter_protocol_declaration_missing"
    ) == (
        'add {"key":"parameter_protocol","scope":"statement","value":"duckdb_prepared"}'
        ' to "environment"'
    )
    assert adapter.suggestion("PIE-B1005", "client_encoding_mismatch") == (
        'the reviewed duckdb value is {"key":"client_encoding","scope":"statement",'
        '"value":"UTF8"}'
    )
    for detail in (
        "inconsistent_declared_scope",
        "source_family_mismatch",
        "source_mapping_missing",
        "complete_ordered_source_schema_required",
        "row_domain_matches_declaration_required",
        "field_domain_premise_mismatch",
        "parameter_occurrence_limit",
        "generated_structure_limit",
        "negative_original_target_evidence",
        "original_enforcement_not_fulfilled",
    ):
        text = adapter.suggestion("PIE-B1001", detail)
        assert text and "postgres:" not in text and "mysql:" not in text
    # The texts the owner agreed to (PL.50), as the route's table states them.
    for detail, text in B2_SUGGESTIONS.items():
        assert adapter.suggestion("PIE-B1003", detail) == text


B2_SUGGESTIONS = {
    "duckdb_relation_shape_not_admitted": (
        "DuckDB emission admits one source read with where, group by, having,"
        " select, order by and limit; JOIN, windows, qualify, distinct, set"
        " operations, relation lets and derived sources are not available on"
        " DuckDB"
    ),
    "duckdb_projection_not_admitted": (
        "select source fields directly, or group by keys and aggregates of"
        " fields, such as select: customer, total = sum(amount); computed values"
        " are not available on DuckDB"
    ),
    "duckdb_aggregate_not_admitted": (
        "use count(), count(field), sum of an Int field, or min or max of an Int"
        " or Float field; other aggregates, sum or avg of a Float and aggregates"
        " of computed values are not available on DuckDB"
    ),
    "duckdb_grouping_not_admitted": (
        "group by source fields, such as group by customer; computed keys are"
        " not available on DuckDB"
    ),
    "duckdb_filter_not_admitted": (
        "compare fields or selected outputs with literals or query parameters of"
        " the same type, and join the tests with and, or and not, such as where"
        " amount >= min_amount and note is not None"
    ),
    "duckdb_order_not_admitted": (
        "order by source fields or selected outputs, such as order by total"
        " desc; computed keys are not available on DuckDB"
    ),
    "duckdb_text_literal_nul_not_admitted": (
        "remove NUL from the Text literal; DuckDB emission writes no NUL into SQL text"
    ),
    "duckdb_parameter_not_admitted": (
        "declare non-null Int, Text, Bool or Float parameters and read each one"
        " in a where or having comparison"
    ),
    "duckdb_field_type_not_admitted": (
        "DuckDB emission reads Int, Text, Bool and Float fields"
    ),
}


def test_a_field_out_of_shape_order_names_the_misplaced_fields(tmp_path: Path) -> None:
    document = contract()
    fields = document["sources"][0]["fields"]
    fields[0], fields[1] = fields[1], fields[0]
    status, emitted = emit(write(tmp_path / "p", PROJECTION, document), PROJECTION)
    assert blockers(emitted) == [
        ("PIE-B1001", "complete_ordered_source_schema_required")
    ]
    related = emitted["blockers"][0]["related"]
    assert [r["line"] for r in related] == [2, 3]  # id and amount


def test_an_expression_scoped_field_premise_must_agree(tmp_path: Path) -> None:
    scope = {
        "kind": "expression",
        "source": {"module": "main.pietto", "kind": "source", "name": "orders"},
        "site": {"kind": "expression_site", "position": 0},
        "context": {"kind": "select_block", "position": 0},
    }
    for value, expected in ((INT["domain"], []), ({"kind": "bool01"}, ["mismatch"])):
        document = contract()
        document["environment"].append(
            {"key": "value_domain", "scope": scope, "value": value}
        )
        root = write(tmp_path / str(len(expected)), PROJECTION, document)
        status, emitted = emit(root, PROJECTION)
        assert status == ("BLOCKED" if expected else "VERIFIED")
        if expected:
            assert blockers(emitted) == [("PIE-B1005", "field_domain_premise_mismatch")]


def test_bind_safe_and_other_families_are_blocked(tmp_path: Path) -> None:
    root = write(tmp_path / "p", PROJECTION, contract())
    status, document = emit(root, PROJECTION, policy="bind-safe")
    assert blockers(document) == [
        ("PIE-B1003", "literal_policy_not_admitted_on_target")
    ]
    header = HEADER + 'source rows: Order = postgres.table("orders")\n'
    body = PROJECTION.replace("from orders", "from rows")
    root = write(tmp_path / "rows", body, contract(), header)
    assert blockers(emit(root, body)[1]) == [
        ("PIE-B1006", "negative_original_target_evidence"),
        ("PIE-B1001", "source_family_mismatch"),
        ("PIE-B1001", "source_mapping_missing"),
    ]


@pytest.mark.parametrize(
    "path,value,error",
    (
        ("target/family", "postgres", "Invalid emission contract structure."),
        ("sources/0/scan", "relation_rows", "Invalid emission contract structure."),
        (
            FIELD0 + "/storage",
            {"kind": "pg_int8"},
            "Storage kind must be one of: arrow_int64, arrow_bool, arrow_string,"
            " arrow_float64.",
        ),
    ),
)
def test_a_contract_of_another_family_is_rejected(
    tmp_path: Path, path: str, value: object, error: str
) -> None:
    document = _change(contract(), path, value)
    status, emitted = emit(write(tmp_path / "p", PROJECTION, document), PROJECTION)
    assert status == "INPUT_REJECTED" and emitted["blockers"] == []
    assert emitted["cli_errors"] == [
        {"kind": "emission_contract_schema", "message": error, "path": path}
    ]


@pytest.mark.parametrize(
    "dialect,control", (("postgres", "mysql.table"), ("mysql", "postgres.table"))
)
def test_postgres_and_mysql_refuse_a_duckdb_source_as_another_family(
    tmp_path: Path, dialect: str, control: str
) -> None:
    """The blockers of a duckdb.arrow source are those of a source of another
    family that these emitters already refuse, in their existing order."""
    entry = source_entry()
    entry["scan"] = "relation_rows"
    entry["relation"] = {"namespace": "public", "name": "orders"}
    storage = {
        "postgres": {"Int": "pg_int8", "Text": "pg_text", "Bool": "pg_bool"},
        "mysql": {"Int": "my_bigint", "Text": "my_varchar", "Bool": "my_bool01"},
    }[dialect]
    for field, (_, kind, _) in zip(entry["fields"], FIELDS, strict=True):
        kind = storage.get(kind, "pg_float8" if dialect == "postgres" else "my_double")
        field["representation"]["storage"] = {"kind": kind} | (
            {"length": 100} if kind == "my_varchar" else {}
        )
    document = contract(entry)
    document["target"] = {
        "family": dialect,
        "release": {"postgres": "18.6", "mysql": "8.4.12"}[dialect],
    }
    results = []
    for connector in ("duckdb.arrow", control):
        header = HEADER.replace("duckdb.arrow", connector)
        root = write(tmp_path / connector, PROJECTION, document, header)
        status, emitted = emit(root, PROJECTION, dialect)
        results.append((status, blockers(emitted)))
    assert results[0] == results[1]
    assert results[0][0] == "BLOCKED"
    assert ("PIE-B1001", "source_family_mismatch") in results[0][1]


@pytest.fixture(scope="module")
def verified(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One VERIFIED emission of the filtered query for the cells that only
    read it, each forgery included: a forgery replaces, never mutates."""
    body = filtered(">=")
    root = write(tmp_path_factory.mktemp("verified") / "p", body, contract())
    outcome, _ = emission_cli.emit_project(
        root,
        "main.pietto",
        "query",
        "result",
        "duckdb",
        "contract.json",
        emission_cli.POLICIES["preserve"],
        read_sources_only=True,
    )
    assert type(outcome) is adapter.DuckDBEmission and outcome.status == "VERIFIED"
    return root, outcome


def test_compile_query_is_built_from_the_verified_document(verified: Any) -> None:
    root, outcome = verified
    query = execution.compile_query(
        root,
        **selected(filtered(">=")),
        dialect="duckdb",
        emission_contract="contract.json",
    )
    assert (query.dialect, query.release, query.literal_policy, query.origin) == (
        "duckdb",
        "2.0.0",
        "preserve",
        "live",
    )
    assert query.slots == () and query.parameters == (("min_amount", "Int", False),)
    assert query.emission == emission_cli.serialize_emission(outcome)
    emission = compile_sql(
        root,
        **selected(filtered(">=")),
        dialect="duckdb",
        emission_contract="contract.json",
    )
    assert query.emission == emission.document
    unset: dict[str, Any] = {"access": None, "premise": None}
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(query, route="postgres_rows", **unset)
    assert refused.value.code == "PIE-R1003"


def test_compile_query_reads_only_the_contract_sources_the_query_reads(
    tmp_path: Path,
) -> None:
    header = HEADER + 'source more: Order = duckdb.arrow("more")\n'
    body = filtered(">=")
    root = write(
        tmp_path / "p", body, contract(source_entry(), source_entry("more")), header
    )
    query = execution.compile_query(
        root, **selected(body), dialect="duckdb", emission_contract="contract.json"
    )
    assert query.emission is not None
    read = json.loads(query.emission)["request"]["contract"]["sources"]
    assert [s["selector"]["name"] for s in read] == ["orders"]
    full = emit(root, body)[1]["request"]["contract"]["sources"]
    assert [s["selector"]["name"] for s in full] == ["orders", "more"]


def test_compile_query_raises_the_blocked_document(tmp_path: Path) -> None:
    body = PROJECTION.replace("        note\n", "        more = amount + 1\n")
    root = write(tmp_path / "p", body, contract())
    with pytest.raises(execution.CompileRejected) as rejected:
        execution.compile_query(
            root, **selected(body), dialect="duckdb", emission_contract="contract.json"
        )
    assert rejected.value.status == "BLOCKED"
    assert (
        rejected.value.emission
        == compile_sql(
            root, **selected(body), dialect="duckdb", emission_contract="contract.json"
        ).document
    )


def _column_read(ast: Any) -> Any:
    """The first result column reads c1 (amount) and is still labelled id."""
    first = dataclasses.replace(ast.columns[0], field=1)
    return dataclasses.replace(ast, columns=(first, *ast.columns[1:]))


def _operator(ast: Any) -> Any:
    return dataclasses.replace(ast, where=dataclasses.replace(ast.where, operator="<="))


def _rendered(artifact: Any, ast: Any) -> dict[str, Any]:
    """An AST rendered and documented afresh: AST, SQL, tokens and document
    agree with each other, and only the plan disagrees."""
    sql, tokens = duckdb_sql.render(ast)
    forged = dataclasses.replace(artifact, ast=ast, sql=sql, tokens=tokens)
    return {
        "ast": ast,
        "sql": sql,
        "tokens": tokens,
        "document": adapter._document(forged),
    }


FORGERIES = {
    "sql": lambda a: {"sql": a.sql.replace(b">=", b"<=")},
    "ast": lambda a: {"ast": dataclasses.replace(a.ast, columns=a.ast.columns[::-1])},
    "tokens": lambda a: {"tokens": a.tokens[1:]},
    "document": lambda a: {"document": a.document.replace(b'"id"', b'"ID"', 1)},
    "column_read": lambda a: _rendered(a, _column_read(a.ast)),
    "operator": lambda a: _rendered(a, _operator(a.ast)),
}


@pytest.mark.parametrize("forgery", FORGERIES)
def test_a_forged_artifact_is_refused(
    verified: Any, monkeypatch: pytest.MonkeyPatch, forgery: str
) -> None:
    """Forgery: a VERIFIED outcome whose artifact was changed after emission."""
    root, outcome = verified
    artifact = outcome.artifact
    forged = dataclasses.replace(
        outcome,
        artifact=dataclasses.replace(artifact, **FORGERIES[forgery](artifact)),
    )
    assert adapter.verify_artifact(artifact) and not adapter.verify_artifact(
        forged.artifact
    )
    if forgery in {"column_read", "operator"}:
        # Every check but the AST's correspondence with the plan holds.
        plan, ast = artifact.checked.plan, forged.artifact.ast
        assert ast != artifact.ast and duckdb_sql.ast_rules_hold(
            ast, len(plan.source_ports), adapter._labels(plan)
        )
        assert duckdb_sql.render(ast) == (forged.artifact.sql, forged.artifact.tokens)
        assert adapter._document(forged.artifact) == forged.artifact.document
    document = json.loads(emission_cli.serialize_emission(forged))
    assert (document["status"], blockers(document)) == (
        "BLOCKED",
        [("PIE-B1008", "artifact_correspondence")],
    )
    monkeypatch.setattr(
        project_public_execution, "emit_live", lambda *arguments: (forged, None)
    )
    with pytest.raises(execution.RequestRejected) as refused:
        execution.compile_query(
            root,
            **selected(filtered(">=")),
            dialect="duckdb",
            emission_contract="contract.json",
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "BINDING_ARTIFACT",
    )


def test_a_forged_grouped_artifact_is_refused(tmp_path: Path) -> None:
    """Forgery: a grouped and ordered AST that keeps every SQL rule, rendered
    and documented afresh, does not correspond to the plan; one that breaks a
    rule is refused by the rules themselves."""
    root = write(tmp_path / "p", ORDERED, contract())
    outcome, _ = emission_cli.emit_project(
        root,
        "main.pietto",
        "query",
        "result",
        "duckdb",
        "contract.json",
        emission_cli.POLICIES["preserve"],
        read_sources_only=True,
    )
    assert type(outcome) is adapter.DuckDBEmission and outcome.status == "VERIFIED"
    artifact: Any = outcome.artifact
    ast, plan = artifact.ast, artifact.checked.plan
    fields, labels = len(plan.source_ports), adapter._labels(plan)
    replace = dataclasses.replace
    columns = list(ast.columns)
    columns[5] = replace(columns[5], function="max")
    first, *rest = ast.order_by
    for forged in (
        replace(ast, columns=tuple(columns)),
        replace(ast, group_by=ast.group_by[::-1]),
        replace(ast, having=replace(ast.having, function="max")),
        replace(ast, having=replace(ast.having, operator="<=")),
        replace(ast, order_by=ast.order_by[::-1]),
        replace(ast, order_by=(replace(first, descending=False), *rest)),
        replace(ast, order_by=(replace(first, function="max"), *rest)),
        replace(ast, order_by=()),
        replace(ast, limit=5),
        replace(ast, limit=None),
    ):
        assert duckdb_sql.ast_rules_hold(forged, fields, labels)
        assert not adapter.verify_artifact(
            replace(artifact, **_rendered(artifact, forged))
        )
    columns = list(ast.columns)
    columns[2] = replace(columns[2], function="sum")
    for broken in (
        replace(ast, columns=tuple(columns)),
        replace(ast, group_by=ast.group_by[:1]),
        replace(ast, having=replace(ast.having, field=0, function=None)),
        replace(ast, having=replace(ast.having, function="avg")),
        replace(ast, group_by=(), having=None),
        replace(ast, order_by=(replace(first, field=1, function=None), *rest)),
        replace(ast, order_by=(replace(first, function="avg"), *rest)),
        replace(ast, order_by=(replace(first, descending=1), *rest)),
        replace(ast, order_by=list(ast.order_by)),
        replace(ast, limit=-1),
        replace(ast, limit=2**63),
        replace(ast, limit=True),
        replace(ast, limit=4.0),
    ):
        assert not duckdb_sql.ast_rules_hold(broken, fields, labels)
    # An aggregate order key needs a grouped statement.
    ungrouped = duckdb_sql.DuckDBSelect(
        duckdb_sql.RELATION,
        (duckdb_sql.DuckDBColumn(0, "id"),),
        None,
        order_by=(duckdb_sql.DuckDBOrderKey(0, "max", False),),
    )
    assert not duckdb_sql.ast_rules_hold(ungrouped, fields, ("id",))
    assert duckdb_sql.ast_rules_hold(
        replace(ungrouped, order_by=(duckdb_sql.DuckDBOrderKey(0, None, True),)),
        fields,
        ("id",),
    )


def test_the_adapter_imports_no_duckdb_pyarrow_or_sqlglot(tmp_path: Path) -> None:
    banned = {"duckdb", "pyarrow", "sqlglot"}
    for path in sorted((REPO_ROOT / "src/pietto/_project").glob("project_duckdb_*.py")):
        imported = REPOSITORY_FACTS.python(path).imported_modules
        assert not {name.partition(".")[0] for name in imported} & banned, path
    body = filtered(">=")
    root = write(tmp_path / "p", body, contract())
    script = (
        f"import sys\nsys.path.insert(0, {str(REPO_ROOT / 'src')!r})\n"
        "from pietto import execution\n"
        "from pietto.compiler import compile_sql\n"
        f"arguments = dict(module='main.pietto', kind='query', name='result',"
        f" dialect='duckdb', emission_contract='contract.json')\n"
        f"assert compile_sql({str(root)!r}, **arguments).status == 'VERIFIED'\n"
        f"execution.compile_query({str(root)!r}, **arguments)\n"
        f"print(sorted(set({sorted(banned)!r}) & {{m.partition('.')[0] for m in sys.modules}}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "[]\n"
