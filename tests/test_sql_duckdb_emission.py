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
from types import SimpleNamespace
from typing import Any

import pytest

from _pietto_repo_facts import REPOSITORY_FACTS
from _pietto_sql_duckdb import (
    FIELDS,
    GROUPED,
    GROUPED_SQL,
    HEADER,
    INT,
    JOINED,
    JOINED_GROUPED,
    JOINED_GROUPED_SQL,
    JOINED_HEADER,
    JOINED_SQL,
    KEYED_HEADER,
    ORDERED,
    ORDERED_SQL,
    PREDICATED,
    PREDICATED_SQL,
    PROJECTION,
    PROJECTION_SQL,
    SELF_GROUPED,
    SELF_GROUPED_SQL,
    SELF_JOINED,
    SELF_JOINED_SQL,
    TWIN_JOINED,
    TWIN_JOINED_SQL,
    TYPED_FIELDS,
    TYPED_HEADER,
    contract,
    filtered,
    joined_contract,
    narrowed,
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
    assert document["target"]["release"] == "2.0.1"
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


def test_predicates_number_each_parameter_at_its_first_read(tmp_path: Path) -> None:
    """PREDICATED's placeholders in the order of first reads in the SQL, one
    per parameter, each read cast to its type and documented as one use of
    its parameter, whose reads list exactly those uses."""
    status, document = emit(write(tmp_path / "p", PREDICATED, contract()), PREDICATED)
    assert (status, document["sql"]) == ("VERIFIED", PREDICATED_SQL)
    sql = document["sql"].encode()
    uses = document["parameter_uses"]
    assert [
        (
            sql[u["range"]["start"] : u["range"]["end"]],
            u["use"],
            u["owner"],
            u["server_index"],
            u["physical_type"],
        )
        for u in uses
    ] == [
        (b"$1", 0, {"kind": "parameter", "parameter": 1}, 1, "duckdb_bigint"),
        (b"$2", 1, {"kind": "parameter", "parameter": 0}, 2, "duckdb_varchar"),
        (b"$3", 2, {"kind": "parameter", "parameter": 2}, 3, "duckdb_boolean"),
        (b"$4", 3, {"kind": "parameter", "parameter": 3}, 4, "duckdb_double"),
        (b"$1", 4, {"kind": "parameter", "parameter": 1}, 1, "duckdb_bigint"),
    ]
    ranges = {(r["start"], r["end"]): r["subject"] for r in document["ranges"]}
    for parameter in document["parameters"]:
        assert parameter["reads"] == [
            ranges[u["range"]["start"], u["range"]["end"]]
            for u in uses
            if u["owner"]["parameter"] == parameter["parameter"]
        ]
    assert [p["name"] for p in document["parameters"]] == [
        "label",
        "low",
        "flag",
        "cap",
    ]
    ends = [(r["start"], r["end"]) for r in document["ranges"]]
    assert ends[0][0] == 0 and ends[-1][1] == len(sql)
    assert all(a[1] == b[0] for a, b in zip(ends, ends[1:]))


# Each literal written with its type and sign, null tests, and NOT of a test.
FILTER_FORMS = {
    "least_int": (
        "amount > -9223372036854775808",
        '"c1" > CAST(-9223372036854775808 AS BIGINT)',
    ),
    "greatest_int": (
        "amount <= 9223372036854775807",
        '"c1" <= CAST(9223372036854775807 AS BIGINT)',
    ),
    "negative_zero": ("price == -0.0", "\"c4\" = CAST('-0.0' AS DOUBLE)"),
    "shortest_float": (
        "price >= 0.000001 and price < 0.1",
        "\"c4\" >= CAST('1e-06' AS DOUBLE) AND \"c4\" < CAST('0.1' AS DOUBLE)",
    ),
    "text": (
        r'''note == "it's a \\ \"q\" é"''',
        '"c2" = ' + "'it''s a \\ \"q\" é'",
    ),
    "bool": ("ok != False", '"c3" <> FALSE'),
    "null_tests": (
        "note is not None or not (ok == True)",
        '"c2" IS NOT NULL OR (NOT "c3" = TRUE)',
    ),
    "literal_on_the_left": ("-5 < amount", 'CAST(-5 AS BIGINT) < "c1"'),
}


@pytest.mark.parametrize("case", FILTER_FORMS)
def test_literals_keep_their_type_and_sign(tmp_path: Path, case: str) -> None:
    where, sql = FILTER_FORMS[case]
    body = (
        f"table result:\n    from orders\n    where {where}\n    select:\n        id\n"
    )
    status, document = emit(write(tmp_path / "p", body, contract()), body)
    prefix = 'SELECT "c0" AS "id" FROM temp.main."pietto_arrow_0" WHERE '
    assert (status, document["sql"]) == ("VERIFIED", prefix + sql)
    assert document["format"] == "pietto.sql-emission.v1"
    assert document["parameter_uses"] == []


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
    "having_literal_or_parameter": (
        _grouped(
            "n = count()", "    having n > 3 or note != p\n", "query result(p: Text):"
        ),
        'SELECT "c2" AS "note", count(*) AS "n" FROM temp.main."pietto_arrow_0"'
        ' GROUP BY "pietto_arrow_0"."c2"'
        ' HAVING count(*) > CAST(3 AS BIGINT) OR "pietto_arrow_0"."c2" <> CAST($1 AS VARCHAR)',
    ),
    # One parameter read in both, one placeholder.
    "where_and_having": (
        _grouped(
            "low = min(price)", "    having low > p\n", "query result(p: Float):"
        ).replace("    group by", "    where price < p\n    group by"),
        'SELECT "c2" AS "note", min("c4") AS "low" FROM temp.main."pietto_arrow_0"'
        ' WHERE "c4" < CAST($1 AS DOUBLE) GROUP BY "pietto_arrow_0"."c2"'
        ' HAVING min("pietto_arrow_0"."c4") > CAST($1 AS DOUBLE)',
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
        ("note", "Text", True, None),
        ("ok", "Bool", False, None),
        ("n", "Int", False, None),
        ("filled", "Int", False, None),
        ("c1", "Int", True, None),
        ("low", "Float", True, None),
        ("high", "Int", True, None),
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


def test_order_keys_predicates_and_the_limit_count_toward_the_nodes(
    tmp_path: Path,
) -> None:
    """GROUPED's 25 nodes, then a key and its value per order key and the
    limit; PREDICATED's 6 for the statement and its columns and 27 for its
    predicate, one per logical operator, comparison, null test, read,
    literal and placeholder."""
    for body, nodes, expected in (
        (ORDERED, 32, "VERIFIED"),
        (ORDERED, 31, "BLOCKED"),
        (PREDICATED, 33, "VERIFIED"),
        (PREDICATED, 32, "BLOCKED"),
    ):
        limited = contract()
        limited["environment"].append(statement("resource_limits", {"nodes": nodes}))
        root = write(tmp_path / f"{len(body)}-{nodes}", body, limited)
        status, emitted = emit(root, body)
        assert status == expected
        if status == "BLOCKED":
            assert blockers(emitted) == [("PIE-B1007", "generated_structure_limit")]


def test_joins_and_arithmetic_count_toward_the_nodes(tmp_path: Path) -> None:
    """Rule 16 counts per JOIN the JOIN, its relation and its `on` as a
    predicate, and each operand of arithmetic: JOINED's 27 nodes are 2 for
    the statement and its relation, 8 for its columns, 3 for its `where`, 9
    for its INNER JOIN's `and` of two equalities and 5 for its LEFT JOIN;
    SELF_JOINED's 19 are 2, 8, 5 for its JOIN and 4 for its operands; and a
    projection's 12 are 2, 6 for its columns and 4 for its operands."""
    arithmetic = _selected("t = amount + id\n        m = amount * id")
    for name, body, header, document, nodes in (
        ("joined", JOINED, JOINED_HEADER, joined_contract, 27),
        ("self", SELF_JOINED, JOINED_HEADER, lambda: narrowed(joined_contract()), 19),
        ("arithmetic", arithmetic, HEADER, _bounded, 12),
    ):
        for limit, expected in ((nodes, "VERIFIED"), (nodes - 1, "BLOCKED")):
            limited = document()
            limited["environment"].append(
                statement("resource_limits", {"nodes": limit})
            )
            root = write(tmp_path / f"{name}-{limit}", body, limited, header)
            status, emitted = emit(root, body)
            assert status == expected, (name, limit)
            if status == "BLOCKED":
                assert blockers(emitted) == [("PIE-B1007", "generated_structure_limit")]


def test_order_refusals_report_their_sites(tmp_path: Path) -> None:
    """Rule 8a at the first computed key, with the text the owner agreed to,
    and in a grouped query at a key that reads an arithmetic output, alone
    or over a JOIN; rule 5 alone at the `order by` whose key names a renamed
    or computed output, for which the plan is unavailable."""
    computed = (
        PROJECTION + "    order by:\n        id\n        -amount\n        amount + 1\n"
    )
    grouped = (
        "table result:\n    from orders\n    group by price\n    select:\n"
        "        price\n        g = -price\n        n = count()\n"
        "    order by:\n        n desc\n        g\n"
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
        ("grouped", grouped, "duckdb_order_not_admitted", (19, 9)),
        ("renamed", renamed, "duckdb_relation_shape_not_admitted", (15, 5)),
        ("output", output, "duckdb_relation_shape_not_admitted", (15, 5)),
    ):
        status, document = emit(write(tmp_path / name, body, contract()), body)
        assert (status, blockers(document)) == ("BLOCKED", [("PIE-B1003", detail)])
        (blocker,) = document["blockers"]
        location = blocker["location"]
        assert (location["line"], location["column"]) == site
    joined = (
        "table result:\n    from orders\n"
        "    inner join customers on customers.id == orders.amount\n"
        "    group by customers.id\n    select:\n        c = customers.id + 1\n"
        "        n = count()\n    order by:\n        c desc\n"
    )
    root = write(
        tmp_path / "joined", joined, narrowed(joined_contract()), JOINED_HEADER
    )
    status, document = emit(root, joined)
    assert (status, blockers(document)) == (
        "BLOCKED",
        [("PIE-B1003", "duckdb_order_not_admitted")],
    )
    location = document["blockers"][0]["location"]
    assert (location["line"], location["column"]) == (27, 9)
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
    # The key reads arithmetic that rule 7 admits, a computed key.
    "arithmetic_output_order_key": (
        "table result:\n    from orders\n    group by price\n    select:\n"
        "        r = price * 2.0\n        n = count()\n    order by:\n        r\n",
        [("PIE-B1003", "duckdb_order_not_admitted")],
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
    "having_int_with_float": (
        _grouped("n = count()", "    having n > 1.5\n"),
        [("PIE-B1003", "duckdb_filter_not_admitted")],
    ),
    "derived_source": (
        PROJECTION.replace("table result", "table base")
        + "table result:\n    from base\n    select:\n        id\n",
        [("PIE-B1003", "duckdb_relation_shape_not_admitted")],
    ),
    # amount ranges over all of signed 64 bits, so `+ 1` is not proved.
    "computed": (
        PROJECTION.replace("        note\n", "        more = amount + 1\n"),
        [("PIE-B1003", "duckdb_arithmetic_range_not_proved")],
    ),
    # Rule 7c after rules 7a and 7b and before rule 8.
    "arithmetic_in_rule_order": (
        "table result:\n    from orders\n    where amount > id\n"
        "    group by amount\n    select:\n        amount\n"
        "        more = amount + 1\n        mean = avg(amount)\n",
        [
            ("PIE-B1003", "duckdb_aggregate_not_admitted"),
            ("PIE-B1003", "duckdb_arithmetic_range_not_proved"),
            ("PIE-B1003", "duckdb_filter_not_admitted"),
        ],
    ),
    **{
        name: (
            PROJECTION.replace("    select:", f"    where {where}\n    select:"),
            [("PIE-B1003", "duckdb_filter_not_admitted")],
        )
        for name, where in (
            ("two_reads", "amount > id"),
            ("int_with_float", "amount > 1.5"),
            ("float_with_int", "price > 1"),
            ("bare_bool", "ok"),
            ("not_of_a_bare_bool", "not ok"),
            ("computed_side", "-amount > 3"),
            ("plus_sign", "amount > +5"),
            ("double_sign", "amount > - -5"),
            ("two_literals", "amount > 3 and 2 > 1"),
        )
    },
    "parameter_null_test": (
        filtered(">").replace("amount > min_amount", "min_amount is None"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "int_with_a_decimal_parameter": (
        filtered(">", "min_amount: Decimal(10, 2)"),
        [("PIE-B1003", "duckdb_filter_not_admitted")],
    ),
    "decimal_parameter_beyond_38_digits": (
        filtered(">", "min_amount: Decimal(39, 2)"),
        [
            ("PIE-B1003", "duckdb_filter_not_admitted"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
        ],
    ),
    "unread_parameter": (
        filtered(">").replace("amount > min_amount", "amount > 3"),
        [("PIE-B1003", "duckdb_parameter_not_admitted")],
    ),
    "nul_literal": (
        PROJECTION.replace("    select:", '    where note == "a\x00b"\n    select:'),
        [("PIE-B1003", "duckdb_text_literal_nul_not_admitted")],
    ),
    "nul_literal_in_a_projection": (
        PROJECTION.replace("        note\n", '        more = "\x00"\n'),
        [
            ("PIE-B1003", "duckdb_projection_not_admitted"),
            ("PIE-B1003", "duckdb_text_literal_nul_not_admitted"),
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
    # Rule 6 refuses only a statement that reads no source.
    "no_source": (
        "query result:\n    values(id: Int):\n        1\n",
        [
            ("PIE-B1003", "duckdb_relation_shape_not_admitted"),
            ("PIE-B1003", "duckdb_source_count_not_admitted"),
            ("PIE-B1003", "duckdb_projection_not_admitted"),
        ],
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


# Arithmetic: id ranges over [-5, 5] and amount over [0, 1000], so
# their Int arithmetic is proved and written unchecked; a Float + or - fails
# where DuckDB gives an infinity, and a * also where two non-zero operands
# give 0.
OVERFLOW = "error('Pietto Float overflow: the result is outside binary64')"
UNDERFLOW = (
    "error('Pietto Float underflow: a product of two non-zero Float values"
    " rounded to 0; use Int or scale the values')"
)
ARITHMETIC = """query result(w: Float, k: Int):
    from orders
    where amount > k
    select:
        t = amount + id
        d = id - amount
        m = amount * id
        f = price * w
        s = price - -1.5
        g = -price
        h = +price
"""
_W = "CAST($1 AS DOUBLE)"
_S = "\"c4\" - CAST('-1.5' AS DOUBLE)"
ARITHMETIC_SQL = (
    'SELECT "c1" + "c0" AS "t", "c0" - "c1" AS "d", "c1" * "c0" AS "m",'
    f' CASE WHEN isinf("c4" * {_W}) THEN {OVERFLOW}'
    f' WHEN ("c4" * {_W}) = 0 AND "c4" <> 0 AND {_W} <> 0 THEN {UNDERFLOW}'
    f' ELSE ("c4" * {_W}) END AS "f",'
    f' CASE WHEN isinf({_S}) THEN {OVERFLOW} ELSE ({_S}) END AS "s",'
    ' -"c4" AS "g", "c4" AS "h"'
    ' FROM temp.main."pietto_arrow_0" WHERE "c1" > CAST($2 AS BIGINT)'
)


def _bounded() -> dict[str, Any]:
    document = contract()
    fields = document["sources"][0]["fields"]
    fields[0]["representation"]["domain"].update(min="-5", max="5")
    fields[1]["representation"]["domain"].update(min="0", max="1000")
    return document


def test_projection_arithmetic_is_proved_or_checked(tmp_path: Path) -> None:
    """Each Int result's exact range is its column's domain; the projection's
    placeholders come first in SQL order, one use per placeholder; a grouped
    query computes over its keys."""
    status, document = emit(write(tmp_path / "p", ARITHMETIC, _bounded()), ARITHMETIC)
    assert (status, document["sql"]) == ("VERIFIED", ARITHMETIC_SQL)
    finite = {"kind": "finite_float", "format": "binary64"}
    assert [
        (
            c["label"],
            c["logical_type"]["name"],
            c["nullable"],
            c["representation"]["domain"],
            c["correspondence"]["field"],
            c["correspondence"]["computed"]["kind"],
        )
        for c in document["columns"]
    ] == [
        (*column, None, "expression")
        for column in (
            ("t", "Int", False, {"kind": "int_range", "min": "-5", "max": "1005"}),
            ("d", "Int", False, {"kind": "int_range", "min": "-1005", "max": "5"}),
            ("m", "Int", False, {"kind": "int_range", "min": "-5000", "max": "5000"}),
            *((label, "Float", False, finite) for label in "fsgh"),
        )
    ]
    sql = document["sql"].encode()
    assert [
        (sql[u["range"]["start"] : u["range"]["end"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [(b"$1", 1)] * 4 + [(b"$2", 2)]
    grouped = (
        "table result:\n    from orders\n    group by amount\n    select:\n"
        "        amount\n        t = amount - 1\n        n = count()\n"
    )
    status, document = emit(write(tmp_path / "g", grouped, _bounded()), grouped)
    assert (status, document["sql"]) == (
        "VERIFIED",
        'SELECT "c1" AS "amount", "c1" - CAST(1 AS BIGINT) AS "t", count(*) AS "n"'
        ' FROM temp.main."pietto_arrow_0" GROUP BY "pietto_arrow_0"."c1"',
    )
    assert document["columns"][1]["representation"]["domain"] == {
        "kind": "int_range",
        "min": "-1",
        "max": "999",
    }


def _selected(value: str, parameters: str = "") -> str:
    head = f"query result({parameters}):" if parameters else "table result:"
    return f"{head}\n    from orders\n    select:\n        id\n        {value}\n"


# Each refused value is on line 14, after `id`, but the aggregate's on 13.
ARITHMETIC_REFUSALS = {
    "beyond_signed_64": (_selected("t = amount * 10000000000000000"), "range"),
    "int_parameter": (_selected("t = amount + k", "k: Int"), "range"),
    "mixed_types": (_selected("t = amount + 1.5"), "projection"),
    "nested": (_selected("t = amount + id + 1"), "projection"),
    "int_sign": (_selected("t = -amount"), "projection"),
    # A value that reads no field is a constant, as `t = 1.5` is.
    "signed_literal": (_selected("t = -1.5"), "projection"),
    "literals": (_selected("t = 1 + 2"), "projection"),
    "aggregate_operand": (
        "table result:\n    from orders\n    select:\n        t = count() + 1\n",
        "projection",
    ),
}
_DETAILS = {
    "range": "duckdb_arithmetic_range_not_proved",
    "projection": "duckdb_projection_not_admitted",
}


@pytest.mark.parametrize("case", ARITHMETIC_REFUSALS)
def test_unadmitted_arithmetic_is_blocked(tmp_path: Path, case: str) -> None:
    """Rule 7c where an Int result may leave signed 64 bits, an Int parameter
    ranging over all of it; rule 7 for other computed values; each at the
    result field."""
    body, kind = ARITHMETIC_REFUSALS[case]
    status, document = emit(write(tmp_path / "p", body, _bounded()), body)
    assert (status, blockers(document)) == ("BLOCKED", [("PIE-B1003", _DETAILS[kind])])
    (blocker,) = document["blockers"]
    assert blocker["suggestion"] == B2_SUGGESTIONS[_DETAILS[kind]]
    location = blocker["location"]
    line = 13 if case == "aggregate_operand" else 14
    assert (location["line"], location["column"]) == (line, 9)


@pytest.mark.parametrize(
    ("value", "parameters"),
    (
        ("cost + cost", ""),
        ("big - big", ""),
        ("cost * cost", ""),
        ("cost + big", ""),
        ("cost * 2", ""),
        ("-cost", ""),
        ("cost + p", "p: Decimal(12, 2)"),
    ),
)
def test_decimal_arithmetic_is_refused_at_the_result_field(
    tmp_path: Path, value: str, parameters: str
) -> None:
    """Arithmetic takes `Int` or `Float` operands only: a `Decimal` field
    beside itself, another `Decimal`, an `Int` literal or a `Decimal`
    parameter, or under a sign, is rule 7's at the result field, and the
    parameter that only it reads is rule 9's too."""
    body = _selected(f"t = {value}", parameters)
    status, document = emit(_typed(tmp_path / "p", body), body)
    expected = [("PIE-B1003", "duckdb_projection_not_admitted")]
    if parameters:
        expected.append(("PIE-B1003", "duckdb_parameter_not_admitted"))
    assert (status, blockers(document)) == ("BLOCKED", expected)
    location = document["blockers"][0]["location"]
    assert (location["line"], location["column"]) == (14, 9)


@pytest.mark.parametrize(
    "domain",
    [
        {"kind": "int_range", "min": "0", "max": str(2**64)},
        {"kind": "finite_float", "format": "binary64"},
    ],
)
def test_arithmetic_over_a_field_of_another_domain_is_rule_28s(
    tmp_path: Path, domain: dict[str, str]
) -> None:
    """Rule 7c proves nothing from a domain that rule 28 refuses."""
    document = contract()
    document["sources"][0]["fields"][1]["representation"]["domain"] = domain
    body = _selected("t = amount + id")
    status, emitted = emit(write(tmp_path / "p", body, document), body)
    assert (status, blockers(emitted)) == (
        "BLOCKED",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    )


@pytest.mark.parametrize(
    ("value", "placeholders"), [("f = price * w", 4), ("f = price + w", 2)]
)
def test_the_parameter_limit_counts_each_written_placeholder(
    tmp_path: Path, value: str, placeholders: int
) -> None:
    """Rule 15 counts the placeholders that the Float checks repeat, one
    entry of parameter_uses each."""
    body = _selected(value, "w: Float")
    for limit, status in ((placeholders, "VERIFIED"), (placeholders - 1, "BLOCKED")):
        document = _bounded()
        document["environment"].append(
            statement("resource_limits", {"parameters": limit})
        )
        found, emitted = emit(write(tmp_path / str(limit), body, document), body)
        assert found == status
        if status == "VERIFIED":
            assert len(emitted["parameter_uses"]) == placeholders
        else:
            assert blockers(emitted) == [("PIE-B1007", "parameter_occurrence_limit")]


def test_a_parameter_read_in_arithmetic_and_where_is_one_placeholder(
    tmp_path: Path,
) -> None:
    """One Float parameter read by the checked product and by the where is
    $1 at each of its five placeholders."""
    body = (
        "query result(w: Float):\n    from orders\n    where price > w\n"
        "    select:\n        id\n        f = price * w\n"
    )
    status, document = emit(write(tmp_path / "p", body, _bounded()), body)
    assert status == "VERIFIED"
    sql = document["sql"].encode()
    assert [
        (sql[u["range"]["start"] : u["range"]["end"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [(b"$1", 1)] * 5


def test_arithmetic_needs_the_operator_environment(tmp_path: Path) -> None:
    document = _bounded()
    document["environment"] = [
        p for p in document["environment"] if p["key"] != "operator_environment"
    ]
    body = _selected("t = amount + id")
    status, emitted = emit(write(tmp_path / "p", body, document), body)
    assert blockers(emitted) == [
        ("PIE-B1004", "operator_environment_declaration_missing")
    ]


def test_a_forged_arithmetic_column_is_refused(tmp_path: Path) -> None:
    """Forgery: the first column's `+` written as a `-`, or its Int domain
    widened, rendered and documented afresh; only the plan or the proved
    range disagrees."""
    root = write(tmp_path / "p", ARITHMETIC, _bounded())
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
    assert type(outcome) is adapter.DuckDBEmission
    artifact = outcome.artifact
    assert artifact is not None and adapter.verify_artifact(artifact)
    first = artifact.ast.columns[0]
    assert first.value is not None
    value = dataclasses.replace(first.value, operator="-")
    ast = dataclasses.replace(
        artifact.ast,
        columns=(dataclasses.replace(first, value=value), *artifact.ast.columns[1:]),
    )
    assert duckdb_sql.ast_rules_hold(
        ast, len(FIELDS), adapter._labels(artifact.checked.plan)
    )
    forged = dataclasses.replace(artifact, **_rendered(artifact, ast))
    assert not adapter.verify_artifact(forged)
    widened = artifact.document.replace(b'"max":"1005"', b'"max":"1006"', 1)
    assert widened != artifact.document
    assert not adapter.verify_artifact(dataclasses.replace(artifact, document=widened))


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
        "2.0.0",
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


def test_a_later_sources_refusals_come_before_the_first_sources_rule_27(
    tmp_path: Path,
) -> None:
    """Rule 27 of the first source is found before rules 19 and 20 of the
    second, and listed after them, by rule order."""
    header = HEADER + 'source more: Order = postgres.table("more")\n'
    document = _change(contract(), "sources/0/fields/2/representation/nullable", False)
    status, emitted = emit(write(tmp_path / "postgres", JOIN, document, header), JOIN)
    assert (status, blockers(emitted)) == (
        "BLOCKED",
        [
            ("PIE-B1006", "negative_original_target_evidence"),
            ("PIE-B1001", "source_family_mismatch"),
            ("PIE-B1001", "source_mapping_missing"),
            ("PIE-B1002", "nullability_mismatch"),
        ],
    )
    assert [b["location"]["line"] for b in emitted["blockers"][1:]] == [9, 9, 4]


def _joined(tmp_path: Path, body: str) -> tuple[str, dict[str, Any]]:
    return emit(write(tmp_path / "p", body, joined_contract(), JOINED_HEADER), body)


def test_joined_sources_number_their_fields_across_the_inputs(tmp_path: Path) -> None:
    """Fields are c0.. across the inputs in FROM and JOIN order; a source that
    reads the relation of another is an input of its own. Each column names
    its source and its field's ordinal there, and a LEFT JOIN's fields are
    nullable."""
    status, emitted = _joined(tmp_path, JOINED)
    assert (status, emitted["sql"]) == ("VERIFIED", JOINED_SQL)
    assert [
        (
            c["label"],
            c["correspondence"]["source"]["name"],
            c["correspondence"]["field"],
            c["nullable"],
            c["representation"]["nullable"],
        )
        for c in emitted["columns"]
    ] == [
        ("id", "orders", 0, False, False),
        ("name", "customers", 1, False, False),
        ("rate", "buyers", 2, True, True),
        ("buyer", "buyers", 0, True, True),
    ]
    sql = emitted["sql"].encode()
    named = {
        sql[r["start"] : r["end"]].decode(): (r["role"], r["subject"]["kind"])
        for r in emitted["ranges"]
    }
    assert named[" INNER JOIN temp.main."] == ("join", "join")
    assert named['"pietto_arrow_2"'] == ("relation", "definition")
    assert named[" = "] == ("operator", "expression")
    assert b"".join(
        sql[r["start"] : r["end"]] for r in emitted["ranges"]
    ) == sql and all(
        a["end"] == b["start"] for a, b in zip(emitted["ranges"], emitted["ranges"][1:])
    )
    query = execution.compile_query(
        tmp_path / "p",
        **selected(JOINED),
        dialect="duckdb",
        emission_contract="contract.json",
    )
    facts = adapter.execution_facts(query._template)
    assert [(s.key, len(s.fields), s.unique) for s in facts.sources] == [
        ("orders", 5, ()),
        ("customers", 3, ()),
        ("customers", 3, ()),
    ]


def test_aggregates_over_join_rows_read_each_field_from_its_input(
    tmp_path: Path,
) -> None:
    """Grouped, having and order reads are qualified by their own input; the
    route checks every declared key of each input (D79.24)."""
    status, emitted = _joined(tmp_path, JOINED_GROUPED)
    assert (status, emitted["sql"]) == ("VERIFIED", JOINED_GROUPED_SQL)
    query = execution.compile_query(
        tmp_path / "p",
        **selected(JOINED_GROUPED),
        dialect="duckdb",
        emission_contract="contract.json",
    )
    facts = adapter.execution_facts(query._template)
    assert [(s.key, s.unique) for s in facts.sources] == [
        ("orders", ()),
        ("customers", ((0,),)),
    ]


SHAPE_REFUSED = ("PIE-B1003", "duckdb_relation_shape_not_admitted")


@pytest.mark.parametrize(
    "join",
    (
        "right join customers on orders.amount == customers.id",
        "full join customers on orders.amount == customers.id",
        "cross join customers",
        "inner join customers on orders.amount < customers.id",
        "inner join customers on orders.amount != customers.id",
        "inner join customers on orders.amount == orders.id",
        "inner join customers on orders.amount == customers.id or orders.id == 1",
        "inner join customers on orders.amount == customers.id and orders.ok",
        "left join customers on orders.amount == 1 and orders.id == customers.id",
        "inner join customers on orders.amount == customers.rate",
    ),
)
def test_other_joins_are_rule_5_at_the_join(tmp_path: Path, join: str) -> None:
    """A JOIN of another kind, or an `on` that is not an `and` of `==` between
    one field of each side, is refused by rule 5 alone, at its clause; the
    rest of the statement is admitted."""
    body = (
        "table result:\n    from orders\n"
        f"    {join}\n"
        "    left join buyers on buyers.id == orders.id\n"
        "    select:\n        id = orders.id\n"
    )
    status, emitted = _joined(tmp_path, body)
    assert (status, blockers(emitted)) == ("BLOCKED", [SHAPE_REFUSED]), emitted
    assert emitted["blockers"][0]["location"]["line"] == 21
    assert emitted["blockers"][0]["suggestion"] == B2_SUGGESTIONS[SHAPE_REFUSED[1]]


@pytest.mark.parametrize("kind", ("right", "inner"))
def test_a_refused_join_is_rule_5_beside_rules_9_and_8b(
    tmp_path: Path, kind: str
) -> None:
    """D79.28 and D79.29: a refused JOIN is rule 5's alone at its clause,
    beside rule 9 for a parameter that only its `on` reads, at the
    statement, and rule 8b for a NUL `Text` literal there, at the literal;
    a `right join` or an `inner join` whose `on` reads either."""
    join = f"{kind} join customers on orders.amount == customers.id and"
    for head, test, also, site in (
        (
            "query result(least: Int):",
            "customers.id == least",
            "duckdb_parameter_not_admitted",
            (19, 1),
        ),
        (
            "table result:",
            'customers.name == "a\x00b"',
            "duckdb_text_literal_nul_not_admitted",
            (21, 81),
        ),
    ):
        body = (
            f"{head}\n    from orders\n    {join} {test}\n"
            "    select:\n        id = orders.id\n"
        )
        status, emitted = _joined(tmp_path / also, body)
        found = [
            (*blocker, (b["location"]["line"], b["location"]["column"]))
            for blocker, b in zip(blockers(emitted), emitted["blockers"])
        ]
        assert (status, found) == (
            "BLOCKED",
            [(*SHAPE_REFUSED, (21, 5)), ("PIE-B1003", also, site)],
        )


_ANY = "any(c.id == orders.amount for c in customers)"
_INNER = "inner join buyers on buyers.id == orders.id"
_LEFT = "left join buyers on buyers.id == orders.id"


@pytest.mark.parametrize(
    ("stages", "site", "where"),
    (
        # A `where` of any(...) before a JOIN or between JOINs filters them.
        ((f"where {_ANY}", _INNER), (21, 11), None),
        (
            (
                "inner join customers on customers.id == orders.amount",
                "where any(b.id == orders.amount for b in buyers)",
                _LEFT,
            ),
            (22, 11),
            None,
        ),
        # After the JOINs it is the `where`, which rule 8 refuses too.
        ((_INNER, f"where {_ANY}"), (22, 11), 22),
        ((_INNER, f"where not {_ANY}"), (22, 15), 22),
        ((_LEFT, f"where {_ANY}"), (22, 11), 22),
        (
            (
                "inner join customers on customers.id == orders.amount",
                _LEFT,
                f"where {_ANY}",
            ),
            (23, 11),
            23,
        ),
        ((f"where {_ANY}",), (21, 11), 21),
        # A refused JOIN before it is the first refused stage.
        (
            ("right join buyers on buyers.id == orders.id", f"where {_ANY}"),
            (21, 5),
            22,
        ),
    ),
)
def test_an_any_filter_is_rule_5_at_the_any(
    tmp_path: Path,
    stages: tuple[str, ...],
    site: tuple[int, int],
    where: int | None,
) -> None:
    """An `any(...)` filter before, between or after admitted JOINs, or with
    none, is refused by rule 5 at the `any(...)`, never at an admitted JOIN
    or at the statement, whatever source it reads; rule 8 also refuses it in
    the `where` after the JOINs."""
    body = (
        "table result:\n    from orders\n"
        + "".join(f"    {stage}\n" for stage in stages)
        + "    select:\n        id = orders.id\n"
    )
    status, emitted = _joined(tmp_path, body)
    found = [
        (code, detail, (b["location"]["line"], b["location"]["column"]))
        for (code, detail), b in zip(blockers(emitted), emitted["blockers"])
    ]
    filtered = [("PIE-B1003", "duckdb_filter_not_admitted", (where, 5))]
    assert (status, found) == (
        "BLOCKED",
        [(*SHAPE_REFUSED, site), *(filtered if where else [])],
    )


def test_arithmetic_over_left_join_rows_is_null_on_the_joined_side(
    tmp_path: Path,
) -> None:
    """Arithmetic reads JOIN rows as a projection does: its Int range is
    proved from each input's int_range, and a column whose operand lies on a
    LEFT JOIN's joined side is nullable, a declared non-null field too, while
    over an INNER JOIN it keeps its operands' declared nullability."""
    document = narrowed(joined_contract())
    body = (
        "table result:\n    from orders\n"
        "    left join customers on orders.amount == customers.id\n"
        "    select:\n        id = orders.id\n        s = orders.amount + customers.id\n"
        "        r = customers.rate * orders.price\n        d = orders.id - orders.amount\n"
    )
    status, emitted = emit(write(tmp_path / "p", body, document, JOINED_HEADER), body)
    assert status == "VERIFIED", emitted
    assert emitted["sql"].startswith(
        'SELECT "c0" AS "id", "c1" + "c5" AS "s", CASE WHEN isinf("c7" * "c4")'
    )
    assert [
        (c["label"], c["nullable"], c["representation"]["domain"].get("max"))
        for c in emitted["columns"]
    ] == [
        ("id", False, "1000"),
        ("s", True, "2000"),
        ("r", True, None),
        ("d", False, "2000"),
    ]
    # An INNER JOIN keeps its operands' declared nullability.
    inner = body.replace("left join", "inner join")
    status, emitted = emit(write(tmp_path / "i", inner, document, JOINED_HEADER), inner)
    assert status == "VERIFIED", emitted
    assert [
        (c["nullable"], c["representation"]["domain"].get("max"))
        for c in emitted["columns"][:2]
    ] == [(False, "1000"), (False, "2000")]
    # Over the default ranges of all signed 64 bits the product is not proved.
    wide = (
        "table result:\n    from orders\n"
        "    inner join customers on orders.amount == customers.id\n"
        "    select:\n        id = orders.id\n        p = orders.amount * customers.id\n"
    )
    status, emitted = _joined(tmp_path / "w", wide)
    assert (status, blockers(emitted)) == (
        "BLOCKED",
        [("PIE-B1003", "duckdb_arithmetic_range_not_proved")],
    )


CHAINED = """table result:
    from orders
    {0} join customers on customers.id == orders.amount
    {1} join buyers on buyers.id == orders.id
    select:
        id = orders.id
        c = customers.id + orders.id
        b = buyers.id + orders.id
"""


@pytest.mark.parametrize(("first", "second"), (("inner", "left"), ("left", "inner")))
def test_arithmetic_is_nullable_by_the_kind_of_its_own_reads_join(
    tmp_path: Path, first: str, second: str
) -> None:
    """In a chain of JOINs, arithmetic over a read is nullable when that
    read's own JOIN is a LEFT JOIN, whatever the kind of the JOIN before or
    after it."""
    body = CHAINED.format(first, second)
    document = narrowed(joined_contract())
    status, emitted = emit(write(tmp_path / "p", body, document, JOINED_HEADER), body)
    assert status == "VERIFIED", emitted
    assert [
        (c["label"], c["nullable"], c["representation"]["nullable"])
        for c in emitted["columns"]
    ] == [
        ("id", False, False),
        ("c", first == "left", first == "left"),
        ("b", second == "left", second == "left"),
    ]


@pytest.mark.parametrize(
    "key,refused",
    (("day", False), ("at", False), ("cost", True)),
)
def test_a_date_or_timestamp_key_joins_and_a_decimal_key_is_rule_5(
    tmp_path: Path, key: str, refused: bool
) -> None:
    """A JOIN key may be a `Date` or a `Timestamp`; a `Decimal` key is refused
    by rule 5 alone, at the JOIN."""
    header = TYPED_HEADER + 'source later: Event = duckdb.arrow("later")\n'
    document = contract(
        source_entry(fields=TYPED_FIELDS), source_entry("later", TYPED_FIELDS)
    )
    body = (
        "table result:\n    from orders\n"
        f"    inner join later on orders.{key} == later.{key}\n"
        "    select:\n        id = orders.id\n        other = later.id\n"
    )
    status, emitted = emit(write(tmp_path / "p", body, document, header), body)
    if refused:
        assert (status, blockers(emitted)) == ("BLOCKED", [SHAPE_REFUSED])
    else:
        assert (status, emitted["sql"]) == (
            "VERIFIED",
            'SELECT "c0" AS "id", "c5" AS "other" FROM temp.main."pietto_arrow_0"'
            ' INNER JOIN temp.main."pietto_arrow_1"'
            f' ON "c{TYPED_KEYS[key]}" = "c{TYPED_KEYS[key] + 5}"',
        )


TYPED_KEYS = {name: k for k, (name, _kind, _nullable) in enumerate(TYPED_FIELDS)}


@pytest.mark.parametrize("logical", ("UUID", "Decimal", "Decimal(39, 2)"))
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
    assert emit(root, JOIN)[0] == "VERIFIED"
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
    # The plan's single-match obligation is beyond the relational shape.
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        SHAPE_REFUSED,
        ("PIE-B1006", "original_enforcement_not_fulfilled"),
    ]


def test_suggestions_are_the_routes_or_the_existing_texts() -> None:
    assert adapter.suggestion("PIE-B1003", "target_release_not_reviewed") == (
        'the reviewed duckdb release is "2.0.1"'
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
    # The texts of the route's table.
    for detail, text in B2_SUGGESTIONS.items():
        assert adapter.suggestion("PIE-B1003", detail) == text


B2_SUGGESTIONS = {
    "duckdb_relation_shape_not_admitted": (
        "DuckDB emission admits duckdb.arrow source reads joined by inner or"
        " left joins on equalities of fields of one type, such as inner join"
        " customers on orders.customer_id == customers.id, then where, group"
        " by, having, select, order by and limit; right, full and cross joins,"
        " other on conditions, Decimal join keys, windows, qualify, distinct,"
        " set operations, relation lets and derived sources are not available"
        " on DuckDB"
    ),
    "duckdb_source_count_not_admitted": (
        "read one or more duckdb.arrow sources; the DuckDB route runs one query"
        " over the Arrow tables passed to execute()"
    ),
    "source_identifier_unrepresentable": (
        'use the relation namespace "arrow"; the DuckDB route reads registered'
        " Arrow tables"
    ),
    "duckdb_projection_not_admitted": (
        "select source fields directly, or group by keys and aggregates of"
        " fields, such as select: customer, total = sum(amount), or add,"
        " subtract or multiply two Int or two Float values, one at least a"
        " field or key, such as net = price - discount; other computed values"
        " are not available on DuckDB"
    ),
    "duckdb_arithmetic_range_not_proved": (
        "narrow the int_range of each Int field this value reads so that"
        " every result fits a signed 64-bit integer; DuckDB emission proves"
        " Int arithmetic from those ranges and literals, and an Int parameter"
        " may hold any signed 64-bit value"
    ),
    "duckdb_aggregate_not_admitted": (
        "use count(), count(field), sum of an Int field, or min or max of an Int,"
        " Float, Decimal, Date or Timestamp field; other aggregates, sum or avg"
        " of a Float or a Decimal and aggregates of computed values are not"
        " available on DuckDB"
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
        "declare non-null Int, Text, Bool, Float, Date, Timestamp or Decimal(p, s)"
        " parameters, p at most 38, and read each one in a where or having"
        " comparison or in selected arithmetic"
    ),
    "duckdb_field_type_not_admitted": (
        "DuckDB emission reads Int, Text, Bool, Float, Date and Timestamp fields"
        " and Decimal(p, s) fields with p at most 38"
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
            " arrow_float64, arrow_date32, arrow_timestamp_us, arrow_decimal128.",
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
        "2.0.1",
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


def _facts(root: Path, body: str) -> Any:
    query = execution.compile_query(
        root, **selected(body), dialect="duckdb", emission_contract="contract.json"
    )
    return adapter.execution_facts(query._template)


def test_a_source_read_twice_is_two_reads_as_two_sources_of_one_key_are(
    tmp_path: Path,
) -> None:
    """A self-join through a row-input alias numbers the fields of each read
    on their own and registers each read under its own name, as two sources
    of one key do, and the route reads each read's input by its key; a
    `where` reads the second read's own field."""
    alias = (
        "table result:\n    from customers\n    let c = customers\n"
        "    inner join c on c.id == customers.id\n"
        "    select:\n        id = customers.id\n        other = c.name\n"
    )
    twice = (
        "table result:\n    from customers\n"
        "    inner join buyers on buyers.id == customers.id\n"
        "    select:\n        id = customers.id\n        other = buyers.name\n"
    )
    sql = (
        'SELECT "c0" AS "id", "c4" AS "other" FROM temp.main."pietto_arrow_0"'
        ' INNER JOIN temp.main."pietto_arrow_1" ON "c3" = "c0"'
    )
    for name, body, other in (
        ("alias", alias, "customers"),
        ("twice", twice, "buyers"),
    ):
        status, emitted = _joined(tmp_path / name, body)
        assert (status, emitted["sql"]) == ("VERIFIED", sql), emitted
        assert [
            (c["correspondence"]["source"]["name"], c["correspondence"]["field"])
            for c in emitted["columns"]
        ] == [("customers", 0), (other, 1)]
        facts = _facts(tmp_path / name / "p", body)
        assert [(s.key, len(s.fields)) for s in facts.sources] == [("customers", 3)] * 2
    status, emitted = _joined(tmp_path / "twin", TWIN_JOINED)
    assert (status, emitted["sql"]) == ("VERIFIED", TWIN_JOINED_SQL)


def test_each_read_of_a_self_join_has_its_own_bounds_and_nullability(
    tmp_path: Path,
) -> None:
    """SELF_JOINED: `parent`'s fields are those of the second read, its Int
    range proved from that read's int_range, and its LEFT JOIN makes them
    nullable, an arithmetic value with an operand among them too, while
    over an INNER JOIN they keep their declared nullability."""
    document = narrowed(joined_contract())
    body = SELF_JOINED
    status, emitted = emit(write(tmp_path / "p", body, document, JOINED_HEADER), body)
    assert (status, emitted["sql"]) == ("VERIFIED", SELF_JOINED_SQL), emitted
    assert [
        (c["label"], c["nullable"], c["representation"]["domain"].get("max"))
        for c in emitted["columns"]
    ] == [
        ("id", False, "1000"),
        ("up", True, "1000"),
        ("s", True, "2000"),
        ("r", True, None),
    ]
    inner = body.replace("left join", "inner join")
    status, emitted = emit(write(tmp_path / "i", inner, document, JOINED_HEADER), inner)
    assert status == "VERIFIED", emitted
    assert [c["nullable"] for c in emitted["columns"]] == [False] * 4


def test_a_self_join_that_aggregates_names_each_read_and_checks_its_keys(
    tmp_path: Path,
) -> None:
    """SELF_GROUPED: grouped, having and order reads are qualified by their
    own read's registered name, and the route checks the declared key of
    each read of the input (D79.24)."""
    root = write(tmp_path / "p", SELF_GROUPED, joined_contract(), KEYED_HEADER)
    status, emitted = emit(root, SELF_GROUPED)
    assert (status, emitted["sql"]) == ("VERIFIED", SELF_GROUPED_SQL), emitted
    facts = _facts(root, SELF_GROUPED)
    assert [(s.key, s.unique) for s in facts.sources] == [("orders", ((0,),))] * 2


def test_a_decimal_where_reads_the_field_of_the_second_read(tmp_path: Path) -> None:
    """A `where` over a `Decimal` field of a JOIN's second read, of one source
    read twice or of a second source of one key, casts its literal to that
    field's own precision and scale."""
    twins = TYPED_HEADER + 'source twins: Event = duckdb.arrow("orders")\n'
    body = (
        "table result:\n    from orders\n{}"
        "    inner join twins on twins.id == orders.id\n"
        "    where twins.cost >= 1.5\n"
        "    select:\n        id = orders.id\n        other = twins.id\n"
    )
    for name, header, alias, sources in (
        ("alias", TYPED_HEADER, "    let twins = orders\n", ()),
        ("twins", twins, "", (source_entry("twins", TYPED_FIELDS, "orders"),)),
    ):
        document = contract(source_entry(fields=TYPED_FIELDS), *sources)
        text = body.format(alias)
        status, emitted = emit(write(tmp_path / name, text, document, header), text)
        assert (status, emitted["sql"]) == (
            "VERIFIED",
            'SELECT "c0" AS "id", "c5" AS "other" FROM temp.main."pietto_arrow_0"'
            ' INNER JOIN temp.main."pietto_arrow_1" ON "c5" = "c0"'
            " WHERE \"c8\" >= CAST('1.5' AS DECIMAL(2,1))",
        ), emitted


def test_a_read_whose_ports_do_not_carry_its_fields_chains_nothing(
    tmp_path: Path,
) -> None:
    """Forgery: a JOIN input whose ports do not carry its source's fields in
    order, each unmodified, chains no source read, so rule 5 refuses it."""
    root = write(tmp_path / "p", TWIN_JOINED, joined_contract(), JOINED_HEADER)
    query = execution.compile_query(
        root,
        **selected(TWIN_JOINED),
        dialect="duckdb",
        emission_contract="contract.json",
    )
    plan = query._template.emission.checked.plan
    names = ("joins", "sources", "join_inputs", "join_ports", "source_ports")
    facts = {name: getattr(plan, name) for name in names}
    assert adapter._chain(SimpleNamespace(**facts)) is not None
    first, read = plan.join_inputs
    ports = {port.ref: port for port in plan.join_ports}
    moved = dataclasses.replace(ports[read.ports[0]], field=ports[read.ports[1]].field)
    for forged in (
        {"join_inputs": (first, dataclasses.replace(read, ports=read.ports[::-1]))},
        {"join_inputs": (first, dataclasses.replace(read, ports=read.ports[:-1]))},
        {
            "join_ports": tuple(
                moved if p.ref is moved.ref else p for p in ports.values()
            )
        },
    ):
        assert adapter._chain(SimpleNamespace(**facts | forged)) is None


def test_a_forged_join_is_refused(tmp_path: Path) -> None:
    """Forgery: a JOIN AST that keeps every SQL rule, rendered and documented
    afresh, does not correspond to the plan; one that breaks a rule is
    refused by the rules themselves."""
    root = write(tmp_path / "p", JOINED, joined_contract(), JOINED_HEADER)
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
    assert fields == 11 and duckdb_sql.ast_rules_hold(ast, fields, labels)
    replace = dataclasses.replace
    first, second = ast.joins
    for forged in (
        replace(ast, joins=(replace(first, kind="LEFT"), second)),
        replace(ast, joins=(first, replace(second, kind="INNER"))),
        replace(ast, joins=(replace(first, on=first.on[::-1]), second)),
        replace(ast, joins=(replace(first, on=first.on[:1]), second)),
        replace(ast, joins=(first, replace(second, on=((0, 8),)))),
        replace(ast, joins=(first, replace(second, on=((9, 0),)))),
        # Its fields then belong to the first JOIN's input.
        replace(ast, joins=(first,)),
    ):
        assert duckdb_sql.ast_rules_hold(forged, fields, labels)
        assert not adapter.verify_artifact(
            replace(artifact, **_rendered(artifact, forged))
        )
    for broken in (
        replace(ast, joins=(replace(first, kind="RIGHT"), second)),
        replace(ast, joins=(replace(first, start=0), second)),
        replace(ast, joins=(first, replace(second, start=5))),
        replace(ast, joins=(first, replace(second, start=11))),
        replace(ast, joins=(replace(first, on=()), second)),
        replace(ast, joins=(replace(first, on=((5, 6),)), second)),
        replace(ast, joins=(replace(first, on=((0, 1),)), second)),
        replace(ast, joins=(replace(first, on=((1, 8),)), second)),
        # One side of an equality in a later input, or before the first.
        replace(ast, joins=(replace(first, on=((6, 9),)), second)),
        replace(ast, joins=(replace(first, on=((-1, 6),)), second)),
        replace(ast, joins=(replace(first, on=[(1, 5)]), second)),
        replace(ast, joins=[first, second]),
    ):
        assert not duckdb_sql.ast_rules_hold(broken, fields, labels)


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
    read = ast.having.left
    for forged in (
        replace(ast, columns=tuple(columns)),
        replace(ast, group_by=ast.group_by[::-1]),
        replace(ast, having=replace(ast.having, left=replace(read, function="max"))),
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
        replace(ast, having=replace(ast.having, left=duckdb_sql.DuckDBRead(0))),
        replace(ast, having=replace(ast.having, left=replace(read, function="avg"))),
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


def _where(predicate: Any) -> Any:
    return duckdb_sql.DuckDBSelect(
        duckdb_sql.RELATION, (duckdb_sql.DuckDBColumn(0, "id"),), predicate
    )


_READ = duckdb_sql.DuckDBRead(1)
_PARAMETER = duckdb_sql.DuckDBParameter(1, "Int")


def _compare(left: Any, right: Any = _PARAMETER) -> Any:
    return duckdb_sql.DuckDBComparison(left, ">", right)


def _literal(value: Any) -> Any:
    return _compare(_READ, duckdb_sql.DuckDBLiteral(value))


# Predicates that break a rule of the route's SQL, each in a `where`.
BROKEN_PREDICATES = {
    "first_placeholder_2": _compare(_READ, duckdb_sql.DuckDBParameter(2, "Int")),
    "placeholder_true": _compare(_READ, duckdb_sql.DuckDBParameter(True, "Int")),
    "placeholder_two_types": duckdb_sql.DuckDBLogic(
        "AND", (_compare(_READ), _compare(_READ, duckdb_sql.DuckDBParameter(1, "Text")))
    ),
    "placeholder_decimal": _compare(_READ, duckdb_sql.DuckDBParameter(1, "Decimal")),
    "nul_literal": _literal("a\x00b"),
    "surrogate_literal": _literal("\ud800"),
    "int_beyond_64_bits": _literal(2**63),
    "infinite_float": _literal(float("inf")),
    "bytes_literal": _literal(b"x"),
    "two_reads": _compare(_READ, duckdb_sql.DuckDBRead(0)),
    "two_constants": _compare(_PARAMETER, duckdb_sql.DuckDBLiteral(3)),
    "aggregate_in_where": _compare(duckdb_sql.DuckDBRead(1, "max")),
    "field_beyond_the_source": _compare(duckdb_sql.DuckDBRead(5)),
    "other_operator": duckdb_sql.DuckDBComparison(_READ, "==", _PARAMETER),
    "null_test_of_a_literal": duckdb_sql.DuckDBNullTest(
        duckdb_sql.DuckDBLiteral(1),  # pyright: ignore[reportArgumentType]
        False,
    ),
    "null_test_flag": duckdb_sql.DuckDBNullTest(
        _READ,
        0,  # pyright: ignore[reportArgumentType]
    ),
    "not_of_two": duckdb_sql.DuckDBLogic("NOT", (_compare(_READ), _compare(_READ))),
    "and_of_one": duckdb_sql.DuckDBLogic("AND", (_compare(_READ),)),
    "xor": duckdb_sql.DuckDBLogic("XOR", (_compare(_READ), _compare(_READ))),
    "operand_list": duckdb_sql.DuckDBLogic(
        "NOT",
        [_compare(_READ)],  # pyright: ignore[reportArgumentType]
    ),
    "bare_read": _READ,
}


@pytest.mark.parametrize("case", BROKEN_PREDICATES)
def test_the_sql_rules_refuse_a_broken_predicate(case: str) -> None:
    assert duckdb_sql.ast_rules_hold(_where(_compare(_READ)), 5, ("id",))
    assert not duckdb_sql.ast_rules_hold(_where(BROKEN_PREDICATES[case]), 5, ("id",))


def _computed(
    operands: Any,
    operator: str = "+",
    tag: str = "Int",
    field: int | None = None,
    function: str | None = None,
) -> Any:
    """`id` and a column `t` of arithmetic over `operands`."""
    value = duckdb_sql.DuckDBArithmetic(operator, operands, tag)
    return duckdb_sql.DuckDBSelect(
        duckdb_sql.RELATION,
        (
            duckdb_sql.DuckDBColumn(0, "id"),
            duckdb_sql.DuckDBColumn(field, "t", function, value),
        ),
        None,
    )


_FLOAT = duckdb_sql.DuckDBRead(4)
# Arithmetic columns that break a rule of the route's SQL.
BROKEN_ARITHMETIC = {
    "field_beside_value": _computed((_READ, _PARAMETER), field=1),
    "function_beside_value": _computed((_READ, _PARAMETER), function="sum"),
    "bool_in_int": _computed((_READ, duckdb_sql.DuckDBLiteral(True))),
    "float_in_int": _computed((_READ, duckdb_sql.DuckDBLiteral(1.0))),
    "int_beyond_64_bits": _computed((_READ, duckdb_sql.DuckDBLiteral(2**63))),
    "int_parameter_in_float": _computed((_FLOAT, _PARAMETER), tag="Float"),
    "placeholder_true": _computed((_READ, duckdb_sql.DuckDBParameter(True, "Int"))),
    "first_placeholder_2": _computed((_READ, duckdb_sql.DuckDBParameter(2, "Int"))),
    "aggregate_operand": _computed((duckdb_sql.DuckDBRead(1, "max"), _PARAMETER)),
    "field_beyond_the_source": _computed((duckdb_sql.DuckDBRead(5), _PARAMETER)),
    "no_read": _computed((duckdb_sql.DuckDBLiteral(1), _PARAMETER)),
    "int_sign": _computed((_READ,), operator="-"),
    "division": _computed((_READ, _PARAMETER), operator="/"),
    "operand_list": _computed([_READ, _PARAMETER]),
}


@pytest.mark.parametrize("case", BROKEN_ARITHMETIC)
def test_the_sql_rules_refuse_broken_arithmetic(case: str) -> None:
    labels = ("id", "t")
    assert duckdb_sql.ast_rules_hold(_computed((_READ, _PARAMETER)), 5, labels)
    assert duckdb_sql.ast_rules_hold(_computed((_FLOAT,), "-", "Float"), 5, labels)
    assert not duckdb_sql.ast_rules_hold(BROKEN_ARITHMETIC[case], 5, labels)


def test_a_forged_predicate_is_refused(tmp_path: Path) -> None:
    """Forgery: predicates that keep every SQL rule, rendered and documented
    afresh, but are not the plan's."""
    root = write(tmp_path / "p", PREDICATED, contract())
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
    replace, where = dataclasses.replace, artifact.ast.where
    left, right = where.operands
    last = right.operands[1]
    tested = right.operands[0].operands[1]
    for forged in (
        replace(where, operator="AND"),
        replace(where, operands=(replace(left, operator="AND"), right)),
        replace(
            where,
            operands=(
                left,
                replace(
                    right,
                    operands=(
                        right.operands[0],
                        replace(last, right=duckdb_sql.DuckDBLiteral(-4)),
                    ),
                ),
            ),
        ),
        replace(
            where,
            operands=(
                left,
                replace(
                    right,
                    operands=(
                        replace(
                            right.operands[0],
                            operands=(
                                right.operands[0].operands[0],
                                replace(tested, negated=True),
                            ),
                        ),
                        last,
                    ),
                ),
            ),
        ),
    ):
        ast = replace(artifact.ast, where=forged)
        assert duckdb_sql.ast_rules_hold(ast, 5, adapter._labels(artifact.checked.plan))
        assert not adapter.verify_artifact(
            replace(artifact, **_rendered(artifact, ast))
        )


def test_a_literal_of_another_type_or_sign_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forgery: a literal swapped for an equal value of another type or sign,
    rendered and documented afresh. The ASTs compare equal; the SQL does
    not, and the artifact is refused."""
    cases = (
        ("amount == 1", (True, 1.0)),
        ("price == -0.0", (0.0,)),
        ("ok == True", (1, 1.0)),
    )
    last: tuple[Any, Any, Path, str] | None = None
    for where, values in cases:
        body = f"table result:\n    from orders\n    where {where}\n    select:\n        id\n"
        root = write(tmp_path / where.split()[0], body, contract())
        outcome, _ = emission_cli.emit_project(
            root,
            "main.pietto",
            "table",
            "result",
            "duckdb",
            "contract.json",
            emission_cli.POLICIES["preserve"],
            read_sources_only=True,
        )
        assert type(outcome) is adapter.DuckDBEmission and outcome.status == "VERIFIED"
        artifact: Any = outcome.artifact
        plan = artifact.checked.plan
        for value in values:
            right = duckdb_sql.DuckDBLiteral(value)
            ast = dataclasses.replace(
                artifact.ast, where=dataclasses.replace(artifact.ast.where, right=right)
            )
            assert ast == artifact.ast and duckdb_sql.ast_rules_hold(
                ast, 5, adapter._labels(plan)
            )
            forged = dataclasses.replace(artifact, **_rendered(artifact, ast))
            assert not adapter.verify_artifact(forged)
            last = (outcome, forged, root, body)
    assert last is not None
    outcome, forged, root, body = last
    monkeypatch.setattr(
        project_public_execution,
        "emit_live",
        lambda *arguments: (dataclasses.replace(outcome, artifact=forged), None),
    )
    with pytest.raises(execution.RequestRejected) as refused:
        execution.compile_query(
            root, **selected(body), dialect="duckdb", emission_contract="contract.json"
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "BINDING_ARTIFACT",
    )


def test_filter_and_parameter_refusals_report_their_sites(tmp_path: Path) -> None:
    """Rule 8b at the literal; rule 9 at the declaration of the first
    parameter in header order that fails, else at the statement."""
    cases = (
        (
            PROJECTION.replace(
                "    select:", '    where note == "x" or note == "a\x00b"\n    select:'
            ),
            ("PIE-B1003", "duckdb_text_literal_nul_not_admitted"),
            (12, 34),
        ),
        (
            filtered(">", "min_amount: Int, b: Int | None, c: Int"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
            (10, 31),
        ),
        (
            filtered(">", "c: Text, min_amount: Int"),
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
            (10, 14),
        ),
        (
            filtered(">=") + "        echo = min_amount\n",
            ("PIE-B1003", "duckdb_parameter_not_admitted"),
            (10, 1),
        ),
    )
    for position, (body, expected, site) in enumerate(cases):
        root = write(tmp_path / str(position), body, contract())
        status, document = emit(root, body)
        (blocker,) = (
            b for b in document["blockers"] if b["subject"]["detail"] == expected[1]
        )
        location = blocker["location"]
        assert (status, location["line"], location["column"]) == ("BLOCKED", *site)
        assert blocker["suggestion"] == B2_SUGGESTIONS[expected[1]]


def _typed(root: Path, body: str, document: dict[str, Any] | None = None) -> Path:
    """A project over TYPED_HEADER's source, with its contract by default."""
    entry = source_entry(fields=TYPED_FIELDS)
    return write(root, body, document or contract(entry), TYPED_HEADER)


TYPED_SELECT = 'SELECT "c0" AS "id" FROM temp.main."pietto_arrow_0" WHERE '


def test_typed_fields_are_read_grouped_and_ordered(tmp_path: Path) -> None:
    """A `Date`, `Timestamp` or `Decimal(p, s)` field is read, grouped and
    ordered, and `count`, `min` and `max` take it; each column keeps its
    field's representation, a Decimal's logical type its (p, s)."""
    body = "table result:\n    from orders\n    select:\n" + "".join(
        f"        {name}\n" for name, _kind, _nullable in TYPED_FIELDS
    )
    status, document = emit(_typed(tmp_path / "read", body), body)
    assert (status, document["sql"]) == (
        "VERIFIED",
        'SELECT "c0" AS "id", "c1" AS "day", "c2" AS "at", "c3" AS "cost",'
        ' "c4" AS "big" FROM temp.main."pietto_arrow_0"',
    )
    decimal = {"precision": 12, "scale": 2}
    assert [
        (c["logical_type"]["name"], c["logical_type"]["parameters"], c["nullable"])
        for c in document["columns"][1:]
    ] == [
        ("Date", None, True),
        ("Timestamp", None, False),
        ("Decimal", decimal, True),
        ("Decimal", {"precision": 38, "scale": 10}, False),
    ]
    assert document["columns"][3]["representation"] == {
        "storage": {"kind": "arrow_decimal128"} | decimal,
        "domain": {"kind": "decimal"} | decimal,
        "nullable": True,
    }
    grouped = (
        "table result:\n    from orders\n    group by day, cost\n    select:\n"
        "        day\n        cost\n        first = min(at)\n"
        "        top = max(big)\n        n = count(at)\n"
        "    order by:\n        day desc\n        top\n"
    )
    root = _typed(tmp_path / "grouped", grouped)
    status, document = emit(root, grouped)
    assert (status, document["sql"]) == (
        "VERIFIED",
        'SELECT "c1" AS "day", "c3" AS "cost", min("c2") AS "first",'
        ' max("c4") AS "top", count("c2") AS "n" FROM temp.main."pietto_arrow_0"'
        ' GROUP BY "pietto_arrow_0"."c1", "pietto_arrow_0"."c3"'
        ' ORDER BY "pietto_arrow_0"."c1" DESC NULLS FIRST,'
        ' max("pietto_arrow_0"."c4") ASC NULLS LAST',
    )
    query = execution.compile_query(
        root, **selected(grouped), dialect="duckdb", emission_contract="contract.json"
    )
    assert adapter.execution_facts(query._template).result == (
        ("day", "Date", True, None),
        ("cost", "Decimal", True, (12, 2)),
        ("first", "Timestamp", True, None),
        ("top", "Decimal", True, (38, 10)),
        ("n", "Int", False, None),
    )


TYPED_FORMS = {
    "date": ('day >= "2024-01-01"', "\"c1\" >= CAST('2024-01-01' AS DATE)"),
    "date_on_the_left": (
        '"9999-12-31" == day',
        "CAST('9999-12-31' AS DATE) = \"c1\"",
    ),
    "timestamp": (
        'at < "2024-01-01 10:00:00.5"',
        "\"c2\" < CAST('2024-01-01 10:00:00.500000' AS TIMESTAMP)",
    ),
    "civil_end": (
        'at <= "9999-12-31 23:59:59.499999"',
        "\"c2\" <= CAST('9999-12-31 23:59:59.499999' AS TIMESTAMP)",
    ),
    # A number literal is the exact decimal it writes, cast to its own
    # precision and scale; a trailing zero is one of its digits.
    "decimal": ("cost > 1_000.5", "\"c3\" > CAST('1000.5' AS DECIMAL(5,1))"),
    "decimal_int": ("cost == 5", "\"c3\" = CAST('5' AS DECIMAL(1,0))"),
    "decimal_signed": ("cost > -0.25", "\"c3\" > CAST('-0.25' AS DECIMAL(2,2))"),
    "decimal_trailing_zero": (
        "cost != 0.120",
        "\"c3\" <> CAST('0.120' AS DECIMAL(3,3))",
    ),
    # A leading zero is not one of its digits.
    "decimal_leading_zeros": (
        "cost == 007 or cost < 00.50",
        "\"c3\" = CAST('7' AS DECIMAL(1,0)) OR \"c3\" < CAST('0.50' AS DECIMAL(2,2))",
    ),
    # Decimal(38, 10) and a literal of scale 10 fit in 38 digits together.
    "decimal_widest": (
        "big < 9999999999999999999999999999.0000000001",
        "\"c4\" < CAST('9999999999999999999999999999.0000000001' AS DECIMAL(38,10))",
    ),
    # The sign is exact on all 38 digits.
    "decimal_widest_signed": (
        "big > -9999999999999999999999999999.0000000001",
        "\"c4\" > CAST('-9999999999999999999999999999.0000000001' AS DECIMAL(38,10))",
    ),
    "null_tests": (
        "day is None or cost is not None",
        '"c1" IS NULL OR "c3" IS NOT NULL',
    ),
}


@pytest.mark.parametrize("case", TYPED_FORMS)
def test_typed_literals_are_cast_to_their_types(tmp_path: Path, case: str) -> None:
    where, sql = TYPED_FORMS[case]
    body = (
        f"table result:\n    from orders\n    where {where}\n    select:\n        id\n"
    )
    status, document = emit(_typed(tmp_path / "p", body), body)
    assert (status, document["sql"]) == ("VERIFIED", TYPED_SELECT + sql)


@pytest.mark.parametrize(
    "literal,expected",
    (
        ("5", ("VERIFIED", TYPED_SELECT + "\"c3\" < CAST('5' AS DECIMAL(1,0))")),
        ("0.5", ("BLOCKED", [("PIE-B1003", "duckdb_filter_not_admitted")])),
    ),
)
def test_an_inlined_literal_beside_a_decimal_needs_no_text_or_is_refused(
    tmp_path: Path, literal: str, expected: tuple[str, Any]
) -> None:
    """An `Int` literal of a def body is its exact value; a `Float` one is
    refused, since its inlined copy has the call's span, not its text."""
    body = (
        f"def cheap(c: Decimal | None) -> Bool | None:\n    return c < {literal}\n\n"
        "table result:\n    from orders\n    where cheap(cost)\n"
        "    select:\n        id\n"
    )
    status, document = emit(_typed(tmp_path / "p", body), body)
    observed = document["sql"] if status == "VERIFIED" else blockers(document)
    assert (status, observed) == expected


def test_typed_parameters_are_cast_to_their_types(tmp_path: Path) -> None:
    body = (
        "query result(since: Timestamp, on: Date, floor: Decimal(12, 2)):\n"
        "    from orders\n    where at >= since and (day == on or cost <= floor)\n"
        "    select:\n        id\n"
    )
    status, document = emit(_typed(tmp_path / "p", body), body)
    assert (status, document["sql"]) == (
        "VERIFIED",
        TYPED_SELECT + '"c2" >= CAST($1 AS TIMESTAMP) AND ("c1" = CAST($2 AS DATE)'
        ' OR "c3" <= CAST($3 AS DECIMAL(12,2)))',
    )
    assert [u["physical_type"] for u in document["parameter_uses"]] == [
        "duckdb_timestamp",
        "duckdb_date",
        "duckdb_decimal",
    ]
    assert [p["tag"] for p in document["parameters"]] == [
        "Timestamp",
        "Date",
        "Decimal",
    ]


FILTER = [("PIE-B1003", "duckdb_filter_not_admitted")]
TYPED_REFUSALS = {
    **{
        name: (f"where {where}", "", FILTER)
        for name, where in (
            ("impossible_date", 'day == "2024-02-30"'),
            ("date_before_1000", 'day > "0999-12-31"'),
            ("date_for_a_timestamp", 'at >= "2024-01-01"'),
            ("timestamp_past_the_civil_end", 'at > "9999-12-31 23:59:59.5"'),
            ("seven_fractional_digits", 'at > "2024-01-01 00:00:00.0000001"'),
            ("t_separator", 'at > "2024-01-01T00:00:00"'),
            # Decimal(12, 2) beside a literal of scale 31 needs 41 digits,
            # Decimal(38, 10) beside one of scale 11 needs 39.
            ("decimal_literal_too_wide", "cost > 0.0000000000000000000000000000001"),
            ("decimal_scale_beyond_38", "big > 0.00000000001"),
        )
    },
    "decimal_parameter_of_another_scale": (
        "where cost > other",
        "other: Decimal(12, 3)",
        FILTER,
    ),
    "decimal_with_a_float_parameter": ("where cost > ratio", "ratio: Float", FILTER),
    "decimal_with_an_int_parameter": ("where cost > n", "n: Int", FILTER),
    # A `having` compares the tier 1 types only (HAVING_TYPES).
    "having_on_a_date_output": (
        "group by cost\n    select:\n        cost\n        first = min(day)\n"
        '    having first > "2024-01-01"',
        "",
        FILTER,
    ),
    "having_on_a_timestamp_output": (
        "group by cost\n    select:\n        cost\n        last = max(at)\n"
        "    having last >= since",
        "since: Timestamp",
        FILTER,
    ),
    # A Decimal output's kind never matches a literal's or a parameter's.
    "having_on_a_decimal_output": (
        "group by day\n    select:\n        day\n        top = max(cost)\n"
        "    having top > 1",
        "",
        FILTER,
    ),
    "sum_of_a_decimal": (
        "group by day\n    select:\n        day\n        total = sum(cost)",
        "",
        [("PIE-B1003", "duckdb_aggregate_not_admitted")],
    ),
}


@pytest.mark.parametrize("case", TYPED_REFUSALS)
def test_typed_forms_beyond_the_route_are_refused(tmp_path: Path, case: str) -> None:
    clauses, parameters, expected = TYPED_REFUSALS[case]
    head = f"query result({parameters}):" if parameters else "table result:"
    body = f"{head}\n    from orders\n    {clauses}\n"
    if "select:" not in clauses:
        body += "    select:\n        id\n"
    status, document = emit(_typed(tmp_path / "p", body), body)
    assert (status, blockers(document)) == ("BLOCKED", expected)


@pytest.mark.parametrize(
    "field,change",
    (
        ("3", {"storage/precision": 13}),
        ("3", {"domain/scale": 3}),
        ("1", {"storage/kind": "arrow_timestamp_us"}),
        ("2", {"domain/kind": "date"}),
        ("4", {"storage/precision": 39, "domain/precision": 39}),
    ),
)
def test_a_typed_representation_must_fit_its_field(
    tmp_path: Path, field: str, change: dict[str, object]
) -> None:
    """Rule 28: a Decimal's storage and domain carry its declared (p, s), and
    a Date or Timestamp has its own storage and domain."""
    document = contract(source_entry(fields=TYPED_FIELDS))
    for path, value in change.items():
        _change(document, f"sources/0/fields/{field}/representation/{path}", value)
    body = "table result:\n    from orders\n    select:\n        id\n"
    status, emitted = emit(_typed(tmp_path / "p", body, document), body)
    assert (status, blockers(emitted)) == (
        "BLOCKED",
        [("PIE-B1002", "physical_storage_or_domain_mismatch")],
    )


@pytest.mark.parametrize(
    "storage",
    (
        {"kind": "arrow_decimal128", "precision": 12},
        {"kind": "arrow_decimal128", "precision": 2, "scale": 3},
        {"kind": "arrow_decimal128", "precision": 0, "scale": 0},
        {"kind": "arrow_date32", "precision": 12, "scale": 2},
    ),
)
def test_a_typed_storage_has_exactly_its_members(
    tmp_path: Path, storage: dict[str, object]
) -> None:
    path = "sources/0/fields/3/representation/storage"
    document = _change(contract(source_entry(fields=TYPED_FIELDS)), path, storage)
    body = "table result:\n    from orders\n    select:\n        id\n"
    status, emitted = emit(_typed(tmp_path / "p", body, document), body)
    assert status == "INPUT_REJECTED" and emitted["cli_errors"]
    assert all(e["path"].startswith(path) for e in emitted["cli_errors"])


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
