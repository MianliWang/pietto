"""Emission of nested relations.

A checked Collect read or Unnest is refused per target where the target does
not admit it: PostgreSQL emits a Collect read of the selected table or query
(D-S08-4), every other Collect read, every Unnest and every MySQL read keep
PIE-B1003. Each Collect column below the refusals is first attached to a real
flat PostgreSQL emission by ``_pietto_sql_nested_collect``: the target, terminal
and capture scope are the ones the flat block read realizes. The real nested
programs after them go through their own verified plans. Every expected
statement is written out.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import sys
from typing import Any

import pytest

import _pietto_execution_nested_oracle as oracle
import _pietto_sql_nested_collect as collecting
from _pietto_plan_nested import (
    HEAD,
    SHAPES,
    UNNEST_PARENT,
    UNNEST_SHAPES,
    emission_contract,
    imported_sources,
    imported_unnest_sources,
    project,
    sources,
)
import pietto.execution as execution
from pietto._project import project_sql_emission_ast as emission_ast
from pietto._project import project_sql_emission_nested as nested
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission_ast import SQLRowQuery, SQLSymbol
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_verification import (
    _collect_group_problems,
    _collect_problems,
    verify_project_sql_emission,
    verify_row_bytes,
)
from pietto.cli import main as cli_main

pytestmark = pytest.mark.ci_workload("general-runtime")

# Each shape's Collect reads, where `collect` is written, in source order.
READS = {
    "closed": [("main.pietto", 20, 18)],
    "top_k": [("main.pietto", 24, 25)],
    "joined_capture": [("main.pietto", 25, 26)],
    "joined_parent": [("main.pietto", 21, 18)],
    "parallel": [("main.pietto", 23, 14), ("main.pietto", 24, 14)],
    "ordered_parent": [("main.pietto", 19, 18)],
    "windowed": [("main.pietto", 22, 18)],
    "staged_capture": [("main.pietto", 24, 25)],
    "distinct_producer": [("main.pietto", 20, 18)],
    "qualify_producer": [("main.pietto", 23, 18)],
    "reader": [("main.pietto", 19, 18)],
    "exists_reader": [("main.pietto", 19, 18)],
    "scalar_reader": [("main.pietto", 19, 18)],
    "imported": [("parent.pietto", 19, 18)],
}
SENTINELS = ("nested_relation", "<nested relation>")


def _project(tmp_path, shape, dialect):
    target = "postgres" if dialect == "postgres" else "mysql"
    files = (
        imported_sources(target)
        if shape == "imported"
        else imported_unnest_sources(target)
        if shape == "unnest_imported"
        else sources(shape, target)
    )
    root = project(tmp_path / f"{shape}-{dialect}", files)
    module = "parent.pietto" if shape.endswith("imported") else "main.pietto"
    (root / "contract.json").write_text(
        emission_contract(target, module), encoding="utf-8"
    )
    return root


def _emit(root, dialect, capsys, *extra):
    code = cli_main(
        [
            "emit-sql",
            "--project",
            str(root),
            "--module",
            "main.pietto",
            "--kind",
            "query",
            "--name",
            "result",
            "--dialect",
            dialect,
            "--emission-contract",
            "contract.json",
            *extra,
        ]
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# PostgreSQL still refuses a Collect read whose parent another relation reads
# (S16); MySQL refuses every one.
POSTGRES_REFUSED = ("reader", "exists_reader", "scalar_reader", "imported")


@pytest.mark.parametrize(
    ("shape", "dialect"),
    (
        *((shape, "mysql") for shape in (*SHAPES, "imported")),
        *((shape, "postgres") for shape in POSTGRES_REFUSED),
    ),
)
def test_a_checked_collect_program_is_blocked_at_each_read(
    tmp_path, capsys, shape, dialect, monkeypatch
):
    root = _project(tmp_path, shape, dialect)
    monkeypatch.chdir(root)
    assert cli_main(["check", "--project", ".", "--format", "json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is True and checked["diagnostics"] == []

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1
    assert document["status"] == "BLOCKED"
    assert document["artifact"] is None
    assert document["cli_errors"] == [] and document["diagnostics"] == []
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (
                item["location"]["path"],
                item["location"]["line"],
                item["location"]["column"],
            ),
        )
        for item in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "collect_not_admitted_on_target",
            {"kind": "collect", "position": position},
            location,
        )
        for position, location in enumerate(READS[shape])
    ]
    assert not any(sentinel in out for sentinel in SENTINELS)

    code, out, text = _emit(root, dialect, capsys, "--format", "text")
    assert code == 1 and out == ""
    assert text.splitlines()[0] == "pietto.sql-emission.v1 BLOCKED"
    assert [line for line in text.splitlines() if line.startswith("blocker")] == [
        "blocker PIE-B1003 UNSUPPORTED_RULE: collect_not_admitted_on_target "
        f"({path}:{line}:{column})"
        for path, line, column in READS[shape]
    ]
    assert not any(sentinel in text for sentinel in SENTINELS)


def test_compile_query_refuses_a_collect_program_with_the_command_document(
    tmp_path, capsys
):
    dialect = "mysql"
    root = _project(tmp_path, "top_k", dialect)
    _, out, _ = _emit(root, dialect, capsys, "--format", "json")

    with pytest.raises(execution.CompileRejected) as error:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
    assert error.value.status == "BLOCKED"
    assert json.loads(error.value.emission) == json.loads(out)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_a_table_function_refusal_precedes_the_collect_refusal(
    tmp_path, capsys, dialect
):
    target = "postgres" if dialect == "postgres" else "mysql"
    files = sources("closed", target)
    files["main.pietto"] = files["main.pietto"].replace(
        "    from rows\n    select:\n        id\n        nested",
        "    from rows\n    where exists series\n    select:\n        id\n        nested",
    ) + (
        "query series:\n    from generate_series(1, 3, 1) as n\n    select:\n        n\n"
    )
    root = project(tmp_path / dialect, files)
    (root / "contract.json").write_text(collecting.contract(target), encoding="utf-8")

    _, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    if dialect == "postgres":
        # Both reads are admitted: the series in its CTE, the Collect lateral.
        assert document["status"] == "VERIFIED"
        assert document["sql"].count(" LEFT JOIN LATERAL (") == 1
        return
    details = [item["subject"]["detail"] for item in document["blockers"]]
    assert details == [
        "table_function_not_admitted_on_target",
        "collect_not_admitted_on_target",
    ]


_COLLECT = ("collect_not_admitted_on_target", "collect", "main.pietto", 21, 18)
# Each Unnest shape's refusals, in source order: the parent's Collect read,
# then each Unnest let.
REFUSALS = {
    **{
        shape: [
            _COLLECT,
            ("unnest_not_admitted_on_target", "unnest", "main.pietto", line, 5),
        ]
        for shape, line in (
            ("unnest_cross", 24),
            ("unnest_inner", 24),
            ("unnest_left", 24),
            ("unnest_left_where", 24),
            ("unnest_left_on_parent", 24),
            ("unnest_left_on_match", 24),
            ("unnest_ordered", 24),
            ("unnest_alias", 25),
            ("unnest_left_joined_parent", 26),
            ("unnest_join_binding", 26),
            ("unnest_cross_joined_parent", 26),
            ("unnest_beside_series", 25),
            ("unnest_captured_exists", 30),
        )
    },
    "unnest_two_bodies": [
        _COLLECT,
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 24, 5),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 30, 5),
    ],
    "unnest_imported": [
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 6, 5),
        ("collect_not_admitted_on_target", "collect", "parent.pietto", 21, 18),
    ],
    "unnest_language": [
        ("collect_not_admitted_on_target", "collect", "main.pietto", 20, 25),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 23, 5),
    ],
    "unnest_inner_nullable": [
        ("collect_not_admitted_on_target", "collect", "main.pietto", 19, 18),
        ("unnest_not_admitted_on_target", "unnest", "main.pietto", 22, 5),
    ],
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", REFUSALS)
def test_a_checked_unnest_program_is_blocked_at_each_let(
    tmp_path, capsys, shape, dialect, monkeypatch
):
    assert set(REFUSALS) == {*UNNEST_SHAPES, "unnest_imported"}
    root = _project(tmp_path, shape, dialect)
    monkeypatch.chdir(root)
    assert cli_main(["check", "--project", ".", "--format", "json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["ok"] is True and checked["diagnostics"] == []

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1
    assert (document["status"], document["artifact"]) == ("BLOCKED", None)
    assert document["cli_errors"] == [] and document["diagnostics"] == []
    expected = REFUSALS[shape]
    if shape == "unnest_beside_series" and dialect == "mysql":
        # The table-function refusal precedes every nested one (D70.05).
        assert document["blockers"][0]["subject"]["detail"] == (
            "table_function_not_admitted_on_target"
        )
        document["blockers"] = document["blockers"][1:]
    # Each kind's references count in source order within a module.
    counts = {"collect": 0, "unnest": 0}
    references = []
    for _, kind, _, _, _ in expected:
        references.append({"kind": kind, "position": counts[kind]})
        counts[kind] += 1
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (
                item["location"]["path"],
                item["location"]["line"],
                item["location"]["column"],
            ),
        )
        for item in document["blockers"]
    ] == [
        ("PIE-B1003", detail, reference, (path, line, column))
        for (detail, _, path, line, column), reference in zip(
            expected, references, strict=True
        )
    ]
    assert not any(sentinel in out for sentinel in SENTINELS)

    code, out, text = _emit(root, dialect, capsys, "--format", "text")
    assert code == 1 and out == ""
    assert text.splitlines()[0] == "pietto.sql-emission.v1 BLOCKED"
    assert [
        line
        for line in text.splitlines()
        if line.startswith("blocker") and "table_function" not in line
    ] == [
        f"blocker PIE-B1003 UNSUPPORTED_RULE: {detail} ({path}:{line}:{column})"
        for detail, _, path, line, column in expected
    ]
    assert not any(sentinel in text for sentinel in SENTINELS)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_compile_query_refuses_an_unnest_program_with_the_command_document(
    tmp_path, capsys, dialect
):
    root = _project(tmp_path, "unnest_left", dialect)
    _, out, _ = _emit(root, dialect, capsys, "--format", "json")

    with pytest.raises(execution.CompileRejected) as error:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect=dialect,
            emission_contract="contract.json",
        )
    assert error.value.status == "BLOCKED"
    assert json.loads(error.value.emission) == json.loads(out)
    assert "unnest_not_admitted_on_target" in out


# A Timestamp JOIN port beside a CROSS JOIN fails the scalar meaning admission;
# the nested refusals still come first, each at its own read or let.
TIMESTAMP_CROSS = {
    "unnest": (
        UNNEST_PARENT.replace(
            "            total\n", "            total\n            created_at\n"
        )
        + "query result:\n    from parent\n    let o = unnest(parent.nested)\n"
        + "    cross join o\n    select:\n        id = parent.id\n"
        + "        total = o.total\n",
        [
            ("collect_not_admitted_on_target", "collect", 22, 18),
            ("unnest_not_admitted_on_target", "unnest", 25, 5),
        ],
    ),
    "collect": (
        "query result:\n    let children:\n        from rows\n        select id\n"
        + "        order by id\n    from rows\n    cross join orders\n    select:\n"
        + "        id = rows.id\n        at = orders.created_at\n"
        + "        nested = collect children\n",
        [("collect_not_admitted_on_target", "collect", 21, 18)],
    ),
}
# On PostgreSQL the selected query's Collect read is admitted, so the flat
# scalar-meaning refusal of the Timestamp JOIN port is the statement's one.
TIMESTAMP_FLAT = ("PIE-B1003", "scalar_meaning_requires_field_projection")


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shape", TIMESTAMP_CROSS)
def test_a_timestamp_beside_a_cross_join_keeps_the_nested_refusals(
    tmp_path, capsys, shape, dialect
):
    target = "postgres" if dialect == "postgres" else "mysql"
    body, expected = TIMESTAMP_CROSS[shape]
    head = HEAD.format(target=target).replace(
        "    created_at: Int\n", "    created_at: Timestamp\n"
    )
    root = project(tmp_path / dialect, {"main.pietto": head + body})
    contract = json.loads(emission_contract(target))
    for item in contract["sources"][1]["fields"]:
        if item["name"] == "created_at":
            item["representation"] = {
                "storage": {
                    "kind": "pg_timestamp" if target == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                },
                "nullable": False,
                "domain": {"kind": "timestamp"},
            }
    (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")

    code, out, _ = _emit(root, dialect, capsys, "--format", "json")
    document = json.loads(out)
    assert code == 1 and document["status"] == "BLOCKED"
    if (shape, dialect) == ("collect", "postgres"):
        assert [
            (item["code"], item["subject"]["detail"], item["location"])
            for item in document["blockers"]
        ] == [(*TIMESTAMP_FLAT, None)]
        return
    assert [
        (
            item["code"],
            item["subject"]["detail"],
            item["subject"]["reference"],
            (item["location"]["line"], item["location"]["column"]),
        )
        for item in document["blockers"]
    ] == [
        ("PIE-B1003", detail, {"kind": kind, "position": 0}, (line, column))
        for detail, kind, line, column in expected
    ]


RHS = '"public"."phase66 rhs é"'
LHS = '"public"."phase66 lhs é"'
CLOSED_TOP = (
    f'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."order.id" AS "c0", '
    f'"s0"."key value" AS "c1", "s0"."order.id" AS "c2" FROM {RHS} AS "s0"), '
    '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
    'ROW_NUMBER() OVER (ORDER BY "t0"."c1" {key}, "t0"."c2" ASC) AS "c1" '
    'FROM "p0" AS "t0" ORDER BY "t0"."c1" {key}, "t0"."c2" ASC LIMIT 2), '
)
CLOSED_PARENT = (
    '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
    f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
    'WHERE ("s1"."order.id" IN (SELECT "e0"."c0" FROM "p1" AS "e0"))) '
    'SELECT "t2"."c0" AS "a", "g0"."n" AS "b", "g0"."a0" AS "id" FROM "p2" AS "t2" '
    'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
    'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") '
    'AS "g0" ON TRUE'
)
CAPTURED_LET = (
    '(SELECT "t0"."c0" AS "c0", ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) '
    'AS "c1" FROM (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" FROM '
    f'(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM {RHS} AS "s0" '
    'WHERE ("s0"."key value" = "s1"."key value")) AS "t1") AS "t0" '
    'ORDER BY "t0"."c1" DESC LIMIT 2)'
)
EXPECTED = {
    # A hidden NULLABLE key first, in either direction, then the output.
    "closed_desc": CLOSED_TOP.format(key="DESC") + CLOSED_PARENT,
    "closed_asc": CLOSED_TOP.format(key="ASC") + CLOSED_PARENT,
    # The Top-K LIMIT stays inside the correlated derived table: per parent.
    "captured": (
        f'SELECT "s1"."order.id" AS "a", "g0"."n" AS "k", "g0"."a0" AS "id" '
        f'FROM {LHS} AS "s1" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM '
        f'{CAPTURED_LET} AS "e0") AS "g0" ON TRUE'
    ),
    # The DISTINCT terminal keeps its bytes; the read wraps it with the ordinal.
    "distinct": (
        f'WITH "p0" ("c0") AS (SELECT "s0"."key value" AS "c0" FROM {RHS} AS "s0"), '
        '"p1" ("c0") AS (SELECT DISTINCT "t0"."c0" AS "c0" FROM "p0" AS "t0" '
        'ORDER BY "t0"."c0" DESC LIMIT 2), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
        'WHERE ("s1"."key value" IN (SELECT "e0"."c0" FROM "p1" AS "e0"))) '
        'SELECT "t2"."c0" AS "a", "g0"."n" AS "b", "g0"."a0" AS "key" '
        'FROM "p2" AS "t2" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM '
        '(SELECT "d0"."c0" AS "c0", ROW_NUMBER() OVER (ORDER BY "d0"."c0" DESC) '
        'AS "c1" FROM "p1" AS "d0") AS "e0") AS "g0" ON TRUE'
    ),
    # Ordered by an aggregate output: the key is the helper copy of it.
    "grouped": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."key value" AS "c0", '
        f'COUNT(*) AS "c1" FROM {RHS} AS "s0" GROUP BY "s0"."key value"), '
        '"p1" ("c0", "c1") AS (SELECT "t1"."c1" AS "c0", "t1"."c1" AS "c1" '
        'FROM "p0" AS "t1"), "p2" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1" FROM "p1" AS "t0" '
        'ORDER BY "t0"."c1" DESC), "p3" ("c0", "c1") AS '
        '(SELECT "s1"."order.id" AS "c0", "s1"."key value" AS "c1" '
        f'FROM {LHS} AS "s1" WHERE ("s1"."order.id" IN '
        '(SELECT "e0"."c0" FROM "p2" AS "e0"))) '
        'SELECT "t3"."c0" AS "a", "g0"."n" AS "b", "g0"."a0" AS "n" '
        'FROM "p3" AS "t3" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p2" AS "e0") '
        'AS "g0" ON TRUE'
    ),
    # The captured let reads the JOIN body's own alias.
    "joined": (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."order.id" AS "c2", '
        f'"m1"."key value" AS "c3" FROM {LHS} AS "m0" INNER JOIN {RHS} AS "m1" '
        'ON ("m0"."order.id" = "m1"."order.id")) '
        'SELECT "t0"."c0" AS "a", "g0"."n" AS "k", "g0"."a0" AS "id" '
        'FROM "p0" AS "t0" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM '
        '(SELECT "t0"."c0" AS "c0", ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) '
        'AS "c1" FROM (SELECT "t1"."c0" AS "c0", "t1"."c0" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        f'FROM {RHS} AS "s0" WHERE ("s0"."key value" = "t0"."c3")) AS "t1") '
        'AS "t0" ORDER BY "t0"."c1" DESC LIMIT 2) AS "e0") AS "g0" ON TRUE'
    ),
    # Siblings: one lateral each, each reading only the parent row.
    "siblings": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        f'"s0"."order.id" AS "c1" FROM {RHS} AS "s0"), '
        '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1" FROM "p0" AS "t0" '
        'ORDER BY "t0"."c1" DESC LIMIT 2) '
        'SELECT "s2"."order.id" AS "a", "g0"."n" AS "x", "g0"."a0" AS "id", '
        '"g1"."n" AS "y", "g1"."a0" AS "id", "g1"."a1" AS "key" '
        f'FROM {LHS} AS "s2" '
        'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") '
        'AS "g0" ON TRUE '
        'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e1"."c0" ORDER BY "e1"."c2") AS "a0", '
        'ARRAY_AGG("e1"."c1" ORDER BY "e1"."c2") AS "a1" FROM '
        '(SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", '
        'ROW_NUMBER() OVER (ORDER BY "t2"."c2" ASC) AS "c2" FROM '
        '(SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", "t2"."c0" AS "c2" FROM '
        '(SELECT "s1"."order.id" AS "c0", "s1"."key value" AS "c1" '
        f'FROM {RHS} AS "s1" WHERE ("s1"."key value" = "s2"."key value")) '
        'AS "t2") AS "t2" ORDER BY "t2"."c2" ASC) AS "e1") AS "g1" ON TRUE'
    ),
    # The parent's own ORDER BY/LIMIT: its projection CTE names the group
    # c1, c1_0 and its result body carries the whole group to the labels.
    "ordered_parent": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        f'"s0"."order.id" AS "c1" FROM {RHS} AS "s0"), '
        '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1" FROM "p0" AS "t0" '
        'ORDER BY "t0"."c1" DESC LIMIT 2), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."key value" AS "c1" FROM {LHS} AS "s1" '
        'WHERE ("s1"."order.id" IN (SELECT "e0"."c0" FROM "p1" AS "e0"))), '
        '"p3" ("c0", "c1", "c1_0", "c2") AS (SELECT "t2"."c0" AS "c0", '
        '"g0"."n" AS "c1", "g0"."a0" AS "c1_0", "t2"."c0" AS "c2" FROM "p2" AS "t2" '
        'LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") '
        'AS "g0" ON TRUE) '
        'SELECT "t2"."c0" AS "a", "t2"."c1" AS "b", "t2"."c1_0" AS "id" '
        'FROM "p3" AS "t2" ORDER BY "t2"."c2" ASC LIMIT 3'
    ),
    # Both capture lines of the let bind to the JOIN body's alias at one read.
    "captures": (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."order.id" AS "c2", '
        f'"m1"."key value" AS "c3" FROM {LHS} AS "m0" INNER JOIN {RHS} AS "m1" '
        'ON ("m0"."order.id" = "m1"."order.id")) '
        'SELECT "t0"."c0" AS "a", "g0"."n" AS "k", "g0"."a0" AS "id" '
        'FROM "p0" AS "t0" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM '
        '(SELECT "t0"."c0" AS "c0", ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) '
        'AS "c1" FROM (SELECT "t1"."c0" AS "c0", "t1"."c0" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        f'FROM {RHS} AS "s0" WHERE (("s0"."key value" = "t0"."c1") AND '
        '("s0"."order.id" = "t0"."c2"))) AS "t1") '
        'AS "t0" ORDER BY "t0"."c1" DESC LIMIT 2) AS "e0") AS "g0" ON TRUE'
    ),
    # A two-child group through the parent's own ORDER BY/LIMIT: each array
    # keeps its own projection column, c1_0 or c1_1, and its child's label.
    "ordered_pair": (
        'WITH "p0" ("c0", "c1", "c1_0", "c1_1", "c2") AS (SELECT '
        '"s1"."order.id" AS "c0", "g0"."n" AS "c1", "g0"."a0" AS "c1_0", '
        '"g0"."a1" AS "c1_1", "s1"."order.id" AS "c2" '
        f'FROM {LHS} AS "s1" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c2") AS "a0", '
        'ARRAY_AGG("e0"."c1" ORDER BY "e0"."c2") AS "a1" FROM '
        '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c2" ASC) AS "c2" FROM '
        '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c0" AS "c2" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        f'FROM {RHS} AS "s0" WHERE ("s0"."key value" = "s1"."key value")) '
        'AS "t1") AS "t0" ORDER BY "t0"."c2" ASC) AS "e0") AS "g0" ON TRUE) '
        'SELECT "t1"."c0" AS "a", "t1"."c1" AS "y", "t1"."c1_0" AS "id", '
        '"t1"."c1_1" AS "key" FROM "p0" AS "t1" ORDER BY "t1"."c2" ASC LIMIT 3'
    ),
    # Two groups through the parent's own ORDER BY/LIMIT, each under its field.
    "ordered_siblings": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        f'"s0"."order.id" AS "c1" FROM {RHS} AS "s0"), '
        '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1" FROM "p0" AS "t0" '
        'ORDER BY "t0"."c1" DESC LIMIT 2), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        f'"s1"."order.id" AS "c1" FROM {RHS} AS "s1"), '
        '"p3" ("c0", "c1") AS (SELECT "t2"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t2"."c1" ASC) AS "c1" FROM "p2" AS "t2" '
        'ORDER BY "t2"."c1" ASC LIMIT 2), '
        '"p4" ("c0", "c1", "c1_0", "c2", "c2_0", "c3") AS (SELECT '
        '"s2"."order.id" AS "c0", "g0"."n" AS "c1", "g0"."a0" AS "c1_0", '
        '"g1"."n" AS "c2", "g1"."a0" AS "c2_0", "s2"."order.id" AS "c3" '
        f'FROM {LHS} AS "s2" LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e0"."c0" ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") '
        'AS "g0" ON TRUE LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", '
        'ARRAY_AGG("e1"."c0" ORDER BY "e1"."c1") AS "a0" FROM "p3" AS "e1") '
        'AS "g1" ON TRUE) '
        'SELECT "t4"."c0" AS "a", "t4"."c1" AS "x", "t4"."c1_0" AS "id", '
        '"t4"."c2" AS "y", "t4"."c2_0" AS "id" FROM "p4" AS "t4" '
        'ORDER BY "t4"."c3" ASC LIMIT 3'
    ),
}
CASES = {
    "closed_desc": (collecting.CLOSED.format(direction=" desc"), {1: 0}),
    "closed_asc": (collecting.CLOSED.format(direction=""), {1: 0}),
    "captured": (collecting.CAPTURED, {1: 0}),
    "distinct": (collecting.DISTINCT, {1: 0}),
    "grouped": (collecting.GROUPED, {1: 0}),
    "joined": (collecting.JOINED, {1: 0}),
    "siblings": (collecting.SIBLINGS, {1: 0, 2: 1}),
    "ordered_parent": (collecting.ORDERED_PARENT, {1: 0}),
    "captures": (collecting.CAPTURES, {1: 0}),
    "ordered_pair": (collecting.ORDERED_PAIR, {1: 0}),
    "ordered_siblings": (collecting.ORDERED_SIBLINGS, {1: 0, 2: 1}),
}


def _collected(tmp_path: Path, case: str):
    body, reads = CASES[case]
    _, artifact = collecting.emit(tmp_path, body)
    return artifact, collecting.collect(artifact, reads)


def _problems(collected, index=0, *, parent=None, column=None):
    return _collect_problems(
        collected.request,
        collected.parent if parent is None else parent,
        collected.columns[index] if column is None else column,
        collected.orders[index],
        collected.limits[index],
    )


def _groups(collected):
    """Every nested group a result body over the parent carries, with it."""
    return tuple(
        (unit, column)
        for unit in collecting.units(collected.query)
        if type(unit) is resulting.RowResultBody and unit.scan.body is collected.parent
        for column in unit.columns
        if type(column) is resulting.ResultGroupColumn
    )


@pytest.mark.parametrize("case", sorted(CASES))
def test_collect_reads_render_one_left_lateral_aggregate_each(
    tmp_path: Path, case: str
) -> None:
    _, collected = _collected(tmp_path, case)
    rendered = collected.render()
    sql = rendered.sql.decode()
    assert sql == EXPECTED[case]
    assert verify_row_bytes(collected.query, rendered)
    assert all(_problems(collected, i) == () for i in range(len(collected.columns)))
    assert all(
        _collect_group_problems(collected.request, result, group) == ()
        for result, group in _groups(collected)
    )
    # One aggregate SELECT per read: COUNT(*) without COALESCE, LEFT ... ON TRUE,
    # and every array ordered by its read's ordinal alone.
    reads = len(CASES[case][1])
    assert sql.count(' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ') == reads
    assert sql.count(" ON TRUE") == reads and "COALESCE" not in sql
    arrays = re.findall(r'ARRAY_AGG\("(e\d+)"\."c\d+" ORDER BY "(e\d+)"\."c\d+"\)', sql)
    assert len(arrays) == sql.count("ARRAY_AGG(") > 0
    assert all(scope == ordered for scope, ordered in arrays)
    # No window function ever runs inside a DISTINCT SELECT.
    for select in re.findall(r"SELECT DISTINCT .*? FROM ", sql):
        assert "ROW_NUMBER" not in select


def test_collect_ordinal_stays_outside_the_terminal_columns(tmp_path: Path) -> None:
    from pietto._project.project_sql_emission_rendering import render_row_sql

    _, artifact = collecting.emit(tmp_path, collecting.CLOSED.format(direction=" desc"))
    query = artifact.ast
    assert type(query) is SQLRowQuery
    target = collecting.block_targets(query)[0]
    terminal = target.producer
    rebuilt = collecting.with_ordinal(artifact.request, terminal)
    assert rebuilt.ordinal is not None and terminal.ordinal is None
    assert rebuilt.ordinal.symbol.name == "c1"
    assert (
        len(rebuilt.columns) == len(rebuilt.cte_columns) == len(terminal.columns) == 1
    )
    assert [s.name for s in rebuilt.cte_columns] == ["c0"]
    changed = replace(target, producer=rebuilt)
    before, after = rows.block_column(target, 0), rows.block_column(changed, 0)
    assert before is not None and after is not None
    assert (after[0], after[1].tag) == (before[0], before[1].tag) == ("c0", "Int")
    # The terminal alone gains the ordinal: its other reader keeps its bytes.
    bodies = tuple(rebuilt if b is terminal else b for b in query.bodies)
    ordinal_only = replace(query, bodies=bodies)
    rendered = render_row_sql(ordinal_only)
    baseline = artifact.rendered.sql.decode()
    assert rendered.sql.decode() == baseline.replace(
        '"p1" ("c0") AS (SELECT "t0"."c0" AS "c0" FROM',
        '"p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", ROW_NUMBER() OVER '
        '(ORDER BY "t0"."c1" DESC, "t0"."c2" ASC) AS "c1" FROM',
    )
    assert '(SELECT "e0"."c0" FROM "p1" AS "e0")' in baseline
    assert verify_row_bytes(ordinal_only, rendered)


def test_a_terminal_without_order_has_no_collect_sequence(tmp_path: Path) -> None:
    _, artifact = collecting.emit(tmp_path, collecting.UNORDERED)
    terminal = collecting.block_targets(artifact.ast)[0].producer
    assert terminal.distinct is not None and terminal.order is None
    body, problem = resulting.build_result_body(
        artifact.request,
        terminal.definition,
        terminal.boundaries,
        terminal.scan.body,
        index=terminal.index,
        final=terminal.final,
        symbol=SQLSymbol,
        ordinal=True,
    )
    assert body is None and problem == (
        "PIE-B1001",
        "collect_terminal_without_order",
        terminal.boundaries[0].ref,
        None,
    )
    assert nested.ordinal_terminal(terminal) is None


def _realize(collected, index, *, target=None, record=None):
    column = collected.columns[index]
    parent = collected.parent
    return nested.realize_collect(
        column.collect if record is None else record,
        column.lateral.target if target is None else target,
        export=column.export,
        position=column.ordinal,
        final=parent.final,
        terminal=parent.terminals[column.ordinal],
    )


def test_realize_collect_refuses_a_terminal_it_cannot_sequence(
    tmp_path: Path,
) -> None:
    artifact, collected = _collected(tmp_path, "siblings")
    column = collected.columns[0]
    target = column.lateral.target
    terminal = target.producer
    flat = collecting.block_targets(artifact.ast)[0]
    record = column.collect
    refused = {
        # The flat terminal, never rebuilt with its ordinal.
        "collect_terminal_without_ordinal": _realize(collected, 0, target=flat),
        # The let's projection stage instead of its terminal.
        "collect_terminal_without_order": _realize(
            collected, 0, target=replace(target, producer=terminal.scan.body)
        ),
        "collect_children_drift": _realize(
            collected, 0, record=replace(record, children=())
        ),
        "collect_read_drift": _realize(
            collected, 0, record=replace(record, use=collected.records[1].use)
        ),
    }
    for detail, (built, problem) in refused.items():
        assert built is None and problem == ("PIE-B1001", detail, record.ref, None)
    assert _realize(collected, 0)[1] is None


# Each corruption: the stand-in it lands in, the Collect column it changes
# (SIBLINGS: 0 is the closed LIMIT let, 1 the captured two-output let) and the
# one rule it breaks.
CORRUPTIONS = {
    "swap_arrays": ("siblings", 1, ("collect_arrays",)),
    # The captured let orders by `id`, which is its own visible c0.
    "array_by_order_key": ("siblings", 1, ("collect_array_order",)),
    "lateral_reads_sibling": ("siblings", 1, ("collect_terminal",)),
    "siblings_joined": ("siblings", 1, ("collect_laterals",)),
    "drop_count": ("siblings", 0, ("collect_carriers",)),
    "flip_ordinal": ("siblings", 0, ("collect_ordinal",)),
    "drop_ordinal_key": ("closed_desc", 0, ("collect_ordinal",)),
    "ordinal_inside_distinct": ("distinct", 0, ("collect_ordinal_placement",)),
    "limit_outside": ("siblings", 0, ("collect_limit",)),
    "projection_stage": ("siblings", 0, ("collect_terminal",)),
    "reorder_carriers": ("siblings", 1, ("collect_carriers",)),
    "wrong_label": ("siblings", 0, ("collect_carriers",)),
    "graft": ("siblings", 0, ("collect_foreign",)),
    "children_reordered": ("siblings", 1, ("collect_children",)),
    "children_truncated": ("siblings", 1, ("collect_children",)),
    "ordinal_missing": ("siblings", 0, ("collect_ordinal_missing",)),
    "captures_dropped": ("siblings", 1, ("collect_capture",)),
    "captures_on_closed": ("siblings", 0, ("collect_capture",)),
    "captures_reordered": ("captures", 0, ("collect_capture",)),
    "captures_truncated": ("captures", 0, ("collect_capture",)),
    "captures_of_another_read": ("captures", 0, ("collect_capture",)),
}


def _corrupted(tmp_path: Path, corruption: str):
    """One valid-looking Collect node change and the parent it lands in."""
    case, index, _ = CORRUPTIONS[corruption]
    _, collected = _collected(tmp_path, case)
    column = collected.columns[index]
    lateral = column.lateral
    target = lateral.target
    unit = target.producer

    def lateral_change(**changes):
        return replace(column, lateral=replace(lateral, **changes))

    def terminal_change(changed_unit, **changes):
        return lateral_change(target=replace(target, producer=changed_unit), **changes)

    def record_change(**changes):
        record = replace(column.collect, **changes)
        return replace(column, collect=record, lateral=replace(lateral, collect=record))

    if corruption == "siblings_joined":
        # The second read's lateral never reaches the parent's FROM.
        parent = replace(collected.parent, laterals=(collected.columns[0].lateral,))
        return collected, parent, column
    if corruption == "swap_arrays":
        changed = lateral_change(arrays=lateral.arrays[::-1])
    elif corruption == "array_by_order_key":
        child, read, _, alias = lateral.arrays[0]
        changed = lateral_change(
            arrays=((child, read, "c0", alias), *lateral.arrays[1:])
        )
    elif corruption == "lateral_reads_sibling":
        changed = lateral_change(target=collected.columns[0].lateral.target)
    elif corruption == "drop_count":
        changed = replace(column, carriers=column.carriers[1:])
    elif corruption == "flip_ordinal":
        ((item, name, direction),) = unit.ordinal.keys
        flip = "asc" if direction == "desc" else "desc"
        flipped = replace(unit.ordinal, keys=((item, name, flip),))
        changed = terminal_change(replace(unit, ordinal=flipped), ordinal=flipped)
    elif corruption == "drop_ordinal_key":
        shorter = replace(unit.ordinal, keys=unit.ordinal.keys[:1])
        changed = terminal_change(replace(unit, ordinal=shorter), ordinal=shorter)
    elif corruption == "ordinal_inside_distinct":
        inside = replace(lateral.ordinal, scope=unit.scan.symbol)
        changed = terminal_change(
            replace(unit, ordinal=inside), ordinal=inside, wrapper=None
        )
    elif corruption == "limit_outside":
        changed = terminal_change(replace(unit, limit=None))
    elif corruption == "projection_stage":
        changed = terminal_change(unit.scan.body)
    elif corruption == "reorder_carriers":
        count, first, second = column.carriers
        changed = replace(column, carriers=(count, second, first))
    elif corruption == "wrong_label":
        count, (read, _, subject) = column.carriers
        changed = replace(column, carriers=(count, (read, "x", subject)))
    elif corruption == "graft":
        _, other = _collected(tmp_path / "other", case)
        changed = record_change(
            **{
                name: getattr(other.records[index], name)
                for name in ("block", "export", "use", "producer", "children")
            }
        )
    elif corruption == "children_reordered":
        changed = record_change(children=column.collect.children[::-1])
    elif corruption == "children_truncated":
        changed = record_change(children=column.collect.children[:1])
    elif corruption == "captures_dropped":
        changed = record_change(captures=())
    elif corruption == "captures_on_closed":
        changed = record_change(captures=collected.records[1].captures)
    elif corruption == "captures_reordered":
        changed = record_change(captures=column.collect.captures[::-1])
    elif corruption == "captures_truncated":
        changed = record_change(captures=column.collect.captures[:1])
    elif corruption == "captures_of_another_read":
        changed = record_change(ref=collecting._CollectRef(0))
    else:
        assert corruption == "ordinal_missing"
        changed = terminal_change(replace(unit, ordinal=None))
    parent, changed = collecting.with_column(collected, column, changed)
    return collected, parent, changed


@pytest.mark.parametrize("corruption", sorted(CORRUPTIONS))
def test_every_collect_corruption_breaks_one_named_rule(
    tmp_path: Path, corruption: str
) -> None:
    _, index, expected = CORRUPTIONS[corruption]
    collected, parent, column = _corrupted(tmp_path, corruption)
    assert _problems(collected, index, parent=parent, column=column) == expected


BYTE_CORRUPTIONS = {
    # CROSS would drop a parent whose lateral ever yields no row.
    "cross": ("closed_desc", " LEFT JOIN LATERAL (", " CROSS JOIN LATERAL (", ""),
    "no_count": ("closed_desc", 'COUNT(*) AS "n", ', "", ""),
    # The LIMIT leaves the collected terminal for the whole statement.
    "limit_outside": ("closed_desc", ' ASC LIMIT 2), "p2"', ' ASC), "p2"', " LIMIT 2"),
    "array_by_key": (
        "siblings",
        'ORDER BY "e1"."c2") AS "a1"',
        'ORDER BY "e1"."c0") AS "a1"',
        "",
    ),
    "wrapper_reads_stage": (
        "distinct",
        'AS "c1" FROM "p1" AS "d0"',
        'AS "c1" FROM "p0" AS "d0"',
        "",
    ),
    "ordinal_direction": (
        "captured",
        'ORDER BY "t0"."c1" DESC) AS "c1"',
        'ORDER BY "t0"."c1" ASC) AS "c1"',
        "",
    ),
    "group_header": ("ordered_parent", '"c1", "c1_0", "c2"', '"c1", "c2", "c1_0"', ""),
}


@pytest.mark.parametrize("corruption", sorted(BYTE_CORRUPTIONS))
def test_collect_bytes_that_differ_from_their_nodes_are_refused(
    tmp_path: Path, corruption: str
) -> None:
    case, before, after, appended = BYTE_CORRUPTIONS[corruption]
    _, collected = _collected(tmp_path, case)
    rendered = collected.render()
    sql = rendered.sql.decode()
    assert sql.count(before) == 1
    changed = sql.replace(before, after) + appended
    assert not verify_row_bytes(
        collected.query, replace(rendered, sql=changed.encode("utf-8"))
    )


def test_a_nested_group_is_carried_whole_and_never_compared(tmp_path: Path) -> None:
    artifact, collected = _collected(tmp_path, "ordered_parent")
    ((result, group),) = _groups(collected)
    assert result.columns[1] is group
    assert group.group is collected.columns[0]
    assert [c[:2] for c in group.carriers] == [("c1", "b"), ("c1_0", "id")]
    assert resulting.node_count(result) == 1 + 1 + 1
    # A group read by an ORDER key is a structural drift, never a comparison.
    parent = collected.parent
    helper = parent.terminals[2]
    forged, problem = _realize_at(collected, 2, helper)
    assert problem is None
    columns = (*parent.columns[:2], forged)
    built, problem = resulting.build_result_body(
        collected.request,
        result.definition,
        result.boundaries,
        replace(parent, columns=columns),
        index=result.index,
        final=result.final,
        symbol=SQLSymbol,
    )
    assert built is None and problem is not None
    assert problem[:2] == ("PIE-B1001", "order_over_nested_group")


GROUP_CORRUPTIONS = (
    "swap_arrays",
    "swap_count",
    "wrong_label",
    "drop_array",
    "foreign_group",
)


@pytest.mark.parametrize("corruption", GROUP_CORRUPTIONS)
def test_a_nested_group_carried_under_other_columns_breaks_its_rule(
    tmp_path: Path, corruption: str
) -> None:
    _, collected = _collected(tmp_path, "ordered_pair")
    ((result, group),) = _groups(collected)
    count, first, second = group.carriers
    assert [c[:2] for c in group.carriers] == [
        ("c1", "y"),
        ("c1_0", "id"),
        ("c1_1", "key"),
    ]
    if corruption == "swap_arrays":
        # Two Int arrays: their element types alone cannot tell them apart.
        changed = replace(
            group,
            carriers=(count, (second[0], *first[1:]), (first[0], *second[1:])),
        )
    elif corruption == "swap_count":
        changed = replace(
            group, carriers=((first[0], *count[1:]), (count[0], *first[1:]), second)
        )
    elif corruption == "wrong_label":
        changed = replace(group, carriers=(count, (first[0], "x", first[2]), second))
    elif corruption == "drop_array":
        changed = replace(group, carriers=(count, first))
    else:
        assert corruption == "foreign_group"
        changed = replace(group, group=replace(group.group))
    body = replace(
        result,
        columns=tuple(changed if c is group else c for c in result.columns),
    )
    assert _collect_group_problems(collected.request, body, changed) == (
        "collect_group",
    )


def test_a_nested_group_carrying_its_sibling_breaks_its_rule(tmp_path: Path) -> None:
    _, collected = _collected(tmp_path, "ordered_siblings")
    (result, x), (_, y) = _groups(collected)
    # x reads y's projection group, built consistently for it, under x's
    # labels: its bytes still replay its nodes, so only the plan can tell.
    changed = replace(
        x,
        projection_port=y.projection_port,
        read=y.read,
        group=y.group,
        carriers=tuple(
            (theirs[0], ours[1], theirs[2])
            for ours, theirs in zip(x.carriers, y.carriers, strict=True)
        ),
    )
    body = replace(
        result, columns=tuple(changed if c is x else c for c in result.columns)
    )
    assert _collect_group_problems(collected.request, body, changed) == (
        "collect_group",
    )
    assert _collect_group_problems(collected.request, body, y) == ()


# One Collect child label at PostgreSQL's 63-byte identifier limit or past it.
LABELLED = """query result:
    let top:
        from rhs
        select:
            {name} = id
        order by:
            id desc
        limit 2
    from lhs
    where lhs.id in top
    select:
        a = lhs.id
        b = lhs.key
{parent_order}"""
PARENT_ORDER = "    order by:\n        lhs.id\n    limit 3\n"


@pytest.mark.parametrize("ordered", (False, True))
def test_collect_child_labels_are_admitted_as_output_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ordered: bool
) -> None:
    tail = PARENT_ORDER if ordered else ""
    _, fits = collecting.emit(
        tmp_path / "fits", LABELLED.format(name="x" * 63, parent_order=tail)
    )
    admitted = collecting.collect(fits, {1: 0})
    assert _problems(admitted) == ()
    _, artifact = collecting.emit(
        tmp_path / "long", LABELLED.format(name="x" * 64, parent_order=tail)
    )
    with monkeypatch.context() as patched:
        # Only a builder that skipped the label admission builds these nodes.
        patched.setattr(
            "pietto._project.project_sql_emission_ast.identifier_valid",
            lambda *_, **__: True,
        )
        collected = collecting.collect(artifact, {1: 0})
    (column,) = collected.columns
    (child,) = column.collect.children
    final = collected.parent.final
    assert final is not ordered
    # The child's label is the selected owner's output label, so the builder
    # refuses it as a flat output label, even when a closed stage reads it.
    # Checked by parts: a failed tuple comparison would print the plan graph.
    built, problem = _realize(collected, 0)
    assert problem is not None
    refused = built is None and problem[2] is child
    assert refused
    assert problem[:2] == ("PIE-B1002", "output_label_unrepresentable")
    assert problem[3] is None
    # The verifier refuses it in the one body that writes it.
    groups = _groups(collected)
    if ordered:
        ((result, group),) = groups
        assert _problems(collected) == ()
        assert _collect_group_problems(collected.request, result, group) == (
            "collect_label",
        )
    else:
        count = len(groups)
        assert count == 0
        assert _problems(collected) == ("collect_label",)


def _realize_at(collected, position, terminal):
    column = collected.columns[0]
    return nested.realize_collect(
        column.collect,
        column.lateral.target,
        export=column.export,
        position=position,
        final=False,
        terminal=terminal,
    )


DISTINCT_PARENT = """query result:
    let top:
        from rhs
        select:
            id
        order by:
            id desc
        limit 2
    from lhs
    where lhs.id in top
    select distinct:
        a = lhs.id
        b = lhs.key
"""


def test_a_distinct_parent_over_a_nested_group_is_a_structural_drift(
    tmp_path: Path,
) -> None:
    _, artifact = collecting.emit(tmp_path, DISTINCT_PARENT)
    query = artifact.ast
    (result,) = (
        u
        for u in collecting.units(query)
        if type(u) is resulting.RowResultBody and u.distinct is not None and u.final
    )
    parent = result.scan.body
    target = collecting.block_targets(query)[0]
    rebuilt = collecting.with_ordinal(artifact.request, target.producer)
    producer = target.use.producer
    definitions = {d.ref: d for d in artifact.request.plan.bindings.definitions}
    record = collecting.collect_record(
        ref=collecting._CollectRef(0),
        block=parent.block.ref,
        export=parent.definition.original.exports[1].ref,
        use=target.use.ref,
        producer=producer,
        children=tuple(p.ref for p in definitions[producer].exports),
        captures=(),
        semantic=None,
        fact=None,
    )
    column, problem = nested.realize_collect(
        record,
        replace(target, producer=rebuilt),
        export=parent.definition.original.exports[1],
        position=1,
        final=False,
        terminal=parent.terminals[1],
    )
    assert problem is None and column is not None
    built, problem = resulting.build_result_body(
        artifact.request,
        result.definition,
        result.boundaries,
        replace(
            parent, columns=(parent.columns[0], column), laterals=(column.lateral,)
        ),
        index=result.index,
        final=result.final,
        symbol=SQLSymbol,
    )
    assert built is None and problem is not None
    assert problem[:2] == ("PIE-B1001", "distinct_over_nested_group")


def test_collect_widths_and_nodes_count_every_physical_column(tmp_path: Path) -> None:
    _, siblings = _collected(tmp_path / "siblings", "siblings")
    top, low = siblings.columns
    # a, then 1 + 1 and 1 + 2 carriers.
    assert nested.physical_width(siblings.parent) == 1 + 2 + 3
    assert nested.physical_width(top.lateral.target.producer) == 1 + 1
    assert nested.physical_width(low.lateral.target.producer) == 2 + 1
    # Lateral: join, SELECT, FROM, alias, ON; count; 3 per array.
    assert nested.node_count(top.lateral) == 5 + 1 + 3
    assert nested.node_count(low.lateral) == 5 + 1 + 6
    # Its ORDER item and LIMIT, then the ordinal and its one key.
    assert resulting.node_count(top.lateral.target.producer) == 1 + 1 + 2
    _, distinct = _collected(tmp_path / "distinct", "distinct")
    (column,) = distinct.columns
    # The wrapper adds SELECT, FROM, its one carried column and its ordinal.
    assert nested.node_count(column.lateral) == 5 + 1 + 3 + 2 + 1 + 2
    assert nested.physical_width(column.lateral.target.producer) == 1
    _, ordered = _collected(tmp_path / "ordered", "ordered_parent")
    assert nested.physical_width(ordered.parent) == 1 + 2 + 1


# -- Real PostgreSQL Collect emission (D-S08-1..10) ---------------------------

ROWS = '"public"."rows"'
ORDERS = '"public"."orders"'
# Each real nested program's whole statement. A closed let's terminal CTE
# carries its ordinal after its visible columns; a captured let renders inside
# its lateral; the parent's own ORDER BY/LIMIT carries each group whole.
EXPECTED_WIRED = {
    "closed": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."id" AS "c0", '
        '"s0"."other" AS "c1", "s0"."id" AS "c2"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t0"."c2" ASC) AS "c2"'
        ' FROM "p0" AS "t0"'
        ' ORDER BY "t0"."c2" ASC) SELECT "s1"."id" AS "id", '
        '"g0"."n" AS "nested", "g0"."a0" AS "id", "g0"."a1" AS "other"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c2") AS "a0", ARRAY_AGG("e0"."c1"'
        ' ORDER BY "e0"."c2") AS "a1" FROM "p1" AS "e0") AS "g0" ON TRUE'
    ),
    "top_k": (
        'SELECT "s1"."id" AS "id", "g0"."n" AS "recent_orders", '
        '"g0"."a0" AS "id", "g0"."a1" AS "total"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c2") AS "a0", ARRAY_AGG("e0"."c1"'
        ' ORDER BY "e0"."c2") AS "a1"'
        ' FROM (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c2" DESC, "t0"."c3" ASC) AS "c2"'
        ' FROM (SELECT "t1"."c0" AS "c0", "t1"."c2" AS "c1", "t1"."c3" AS "c2", '
        '"t1"."c0" AS "c3"'
        ' FROM (SELECT "s0"."id" AS "c0", "s0"."customer_id" AS "c1", '
        '"s0"."total" AS "c2", "s0"."created_at" AS "c3"'
        f' FROM {ORDERS} AS "s0" WHERE ("s0"."customer_id" = "s1"."id")) AS "t1") AS "t0"'
        ' ORDER BY "t0"."c2" DESC, "t0"."c3" ASC LIMIT 2) AS "e0") AS "g0" ON TRUE'
    ),
    "joined_capture": (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."id" AS "c0", '
        '"m0"."other" AS "c1", "m1"."id" AS "c2", "m1"."other" AS "c3"'
        f' FROM {ROWS} AS "m0" INNER JOIN {ROWS} AS "m1" ON ("m0"."id" = "m1"."id")) SELECT "t0"."c0" AS "id", "g0"."n" AS "matched_orders", "g0"."a0" AS "id"'
        ' FROM "p0" AS "t0"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0"'
        ' FROM (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC) AS "c1"'
        ' FROM (SELECT "t1"."c0" AS "c0", "t1"."c0" AS "c1"'
        ' FROM (SELECT "s0"."id" AS "c0", "s0"."customer_id" AS "c1", '
        '"s0"."total" AS "c2", "s0"."created_at" AS "c3"'
        f' FROM {ORDERS} AS "s0" WHERE (("s0"."customer_id" = "t0"."c0") AND ("s0"."id" = "t0"."c2"))) AS "t1") AS "t0"'
        ' ORDER BY "t0"."c1" ASC) AS "e0") AS "g0" ON TRUE'
    ),
    "joined_parent": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."id" AS "c0", "s0"."id" AS "c1"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC) AS "c1"'
        ' FROM "p0" AS "t0" ORDER BY "t0"."c1" ASC)'
        ', "p2" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."id" AS "c0", '
        '"m0"."other" AS "c1", "m1"."id" AS "c2", "m1"."other" AS "c3"'
        f' FROM {ROWS} AS "m0" INNER JOIN {ROWS} AS "m1" ON ("m0"."id" = "m1"."id")) SELECT "t0"."c0" AS "id", "g0"."n" AS "nested", "g0"."a0" AS "id"'
        ' FROM "p2" AS "t0"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") AS "g0" ON TRUE'
    ),
    "parallel": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."id" AS "c0", "s0"."id" AS "c1"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC) AS "c1"'
        ' FROM "p0" AS "t0" ORDER BY "t0"."c1" ASC)'
        ', "p2" ("c0", "c1", "c2") AS (SELECT "s1"."id" AS "c0", '
        '"s1"."total" AS "c1", "s1"."id" AS "c2"'
        f' FROM {ORDERS} AS "s1")'
        ', "p3" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t1"."c2" ASC) AS "c2"'
        ' FROM "p2" AS "t1"'
        ' ORDER BY "t1"."c2" ASC) SELECT "s2"."id" AS "id", "g0"."n" AS "xs", '
        '"g0"."a0" AS "id", "g1"."n" AS "ys", "g1"."a0" AS "id", "g1"."a1" AS "total"'
        f' FROM {ROWS} AS "s2"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") AS "g0" ON TRUE'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e1"."c0"'
        ' ORDER BY "e1"."c2") AS "a0", ARRAY_AGG("e1"."c1"'
        ' ORDER BY "e1"."c2") AS "a1" FROM "p3" AS "e1") AS "g1" ON TRUE'
    ),
    "ordered_parent": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."id" AS "c0", "s0"."id" AS "c1"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC) AS "c1"'
        ' FROM "p0" AS "t0" ORDER BY "t0"."c1" ASC)'
        ', "p2" ("c0", "c1", "c1_0", "c2") AS (SELECT "s1"."id" AS "c0", '
        '"g0"."n" AS "c1", "g0"."a0" AS "c1_0", "s1"."id" AS "c2"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0"'
        ' FROM "p1" AS "e0") AS "g0" ON TRUE) SELECT "t1"."c0" AS "id", '
        '"t1"."c1" AS "nested", "t1"."c1_0" AS "id"'
        ' FROM "p2" AS "t1" ORDER BY "t1"."c2" ASC LIMIT 5'
    ),
    "windowed": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."id" AS "c0", "s0"."id" AS "c1"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC) AS "c1"'
        ' FROM "p0" AS "t0" ORDER BY "t0"."c1" ASC)'
        ', "p2" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."id" AS "c0", '
        '"m0"."other" AS "c1", "m1"."id" AS "c2", "m1"."other" AS "c3"'
        f' FROM {ROWS} AS "m0" INNER JOIN {ROWS} AS "m1" ON ("m0"."id" = "m1"."id"))'
        ', "p3" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", "t0"."c2" AS "c2", "t0"."c3" AS "c3", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c0" ASC) AS "c4"'
        ' FROM "p2" AS "t0")'
        ', "p4" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t2"."c0" AS "c0", '
        '"t2"."c1" AS "c1", "t2"."c2" AS "c2", "t2"."c3" AS "c3", "t2"."c4" AS "c4"'
        ' FROM "p3" AS "t2" WHERE ("t2"."c4" = CAST(1 AS pg_catalog.int8))) SELECT "t3"."c0" AS "id", "t3"."c4" AS "r", "g0"."n" AS "nested", "g0"."a0" AS "id"'
        ' FROM "p4" AS "t3"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") AS "g0" ON TRUE'
    ),
    "distinct_producer": (
        'WITH "p0" ("c0") AS (SELECT "s0"."customer_id" AS "c0"'
        f' FROM {ORDERS} AS "s0")'
        ', "p1" ("c0") AS (SELECT DISTINCT "t0"."c0" AS "c0"'
        ' FROM "p0" AS "t0"'
        ' ORDER BY "t0"."c0" ASC) SELECT "s1"."id" AS "id", '
        '"g0"."n" AS "nested", "g0"."a0" AS "customer_id"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0"'
        ' FROM (SELECT "d0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "d0"."c0" ASC) AS "c1"'
        ' FROM "p1" AS "d0") AS "e0") AS "g0" ON TRUE'
    ),
    "qualify_producer": (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "s0"."id" AS "c0", '
        '"s0"."customer_id" AS "c1", "s0"."total" AS "c2", '
        '"s0"."created_at" AS "c3", '
        'ROW_NUMBER() OVER (ORDER BY "s0"."id" ASC) AS "c4"'
        f' FROM {ORDERS} AS "s0")'
        ', "p1" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4"'
        ' FROM "p0" AS "t1" WHERE ("t1"."c4" = CAST(1 AS pg_catalog.int8)))'
        ', "p2" ("c0", "c1", "c2") AS (SELECT "t2"."c0" AS "c0", '
        '"t2"."c4" AS "c1", "t2"."c0" AS "c2"'
        ' FROM "p1" AS "t2")'
        ', "p3" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t0"."c2" ASC) AS "c2"'
        ' FROM "p2" AS "t0"'
        ' ORDER BY "t0"."c2" ASC) SELECT "s1"."id" AS "id", '
        '"g0"."n" AS "nested", "g0"."a0" AS "id", "g0"."a1" AS "r"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c2") AS "a0", ARRAY_AGG("e0"."c1"'
        ' ORDER BY "e0"."c2") AS "a1" FROM "p3" AS "e0") AS "g0" ON TRUE'
    ),
    "grouped": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."customer_id" AS "c0", '
        'COUNT(*) AS "c1"'
        f' FROM {ORDERS} AS "s0" GROUP BY "s0"."customer_id")'
        ', "p1" ("c0", "c1", "c2", "c3") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c1" AS "c2", "t1"."c0" AS "c3"'
        ' FROM "p0" AS "t1")'
        ', "p2" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t0"."c2" DESC, '
        '"t0"."c3" ASC) AS "c2"'
        ' FROM "p1" AS "t0"'
        ' ORDER BY "t0"."c2" DESC, "t0"."c3" ASC) SELECT "s1"."id" AS "id", '
        '"g0"."n" AS "busiest", "g0"."a0" AS "customer_id", "g0"."a1" AS "n"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c2") AS "a0", ARRAY_AGG("e0"."c1"'
        ' ORDER BY "e0"."c2") AS "a1" FROM "p2" AS "e0") AS "g0" ON TRUE'
    ),
    "nullable_asc": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."id" AS "c0", '
        '"s0"."other" AS "c1", "s0"."id" AS "c2"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" ASC, "t0"."c2" ASC) AS "c1"'
        ' FROM "p0" AS "t0"'
        ' ORDER BY "t0"."c1" ASC, '
        '"t0"."c2" ASC LIMIT 2) SELECT "s1"."id" AS "id", "g0"."n" AS "nested", '
        '"g0"."a0" AS "id"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") AS "g0" ON TRUE'
    ),
    "nullable_desc": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."id" AS "c0", '
        '"s0"."other" AS "c1", "s0"."id" AS "c2"'
        f' FROM {ROWS} AS "s0")'
        ', "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC, "t0"."c2" ASC) AS "c1"'
        ' FROM "p0" AS "t0"'
        ' ORDER BY "t0"."c1" DESC, '
        '"t0"."c2" ASC LIMIT 2) SELECT "s1"."id" AS "id", "g0"."n" AS "nested", '
        '"g0"."a0" AS "id"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0" FROM "p1" AS "e0") AS "g0" ON TRUE'
    ),
    "filtered": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."id" AS "c0", "s1"."other" AS "c1"'
        f' FROM {ROWS} AS "s1" WHERE ("s1"."id" > CAST(0 AS pg_catalog.int8))) SELECT "t3"."c0" AS "id", "g0"."n" AS "totals", "g0"."a0" AS "total"'
        ' FROM "p0" AS "t3"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0"'
        ' FROM (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1"'
        ' FROM (SELECT "t1"."c2" AS "c0", "t1"."c2" AS "c1"'
        ' FROM (SELECT "s0"."id" AS "c0", "s0"."customer_id" AS "c1", '
        '"s0"."total" AS "c2", "s0"."created_at" AS "c3"'
        f' FROM {ORDERS} AS "s0" WHERE ("s0"."customer_id" = "t3"."c0")) AS "t1") AS "t0"'
        ' ORDER BY "t0"."c1" DESC) AS "e0") AS "g0" ON TRUE'
    ),
    "imported_source": (
        'SELECT "s1"."id" AS "id", "g0"."n" AS "recent_orders", "g0"."a0" AS "id"'
        f' FROM {ROWS} AS "s1"'
        ' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ARRAY_AGG("e0"."c0"'
        ' ORDER BY "e0"."c1") AS "a0"'
        ' FROM (SELECT "t0"."c0" AS "c0", '
        'ROW_NUMBER() OVER (ORDER BY "t0"."c1" DESC) AS "c1"'
        ' FROM (SELECT "t1"."c0" AS "c0", "t1"."c0" AS "c1"'
        ' FROM (SELECT "s0"."id" AS "c0", "s0"."customer_id" AS "c1", '
        '"s0"."total" AS "c2", "s0"."created_at" AS "c3"'
        f' FROM {ORDERS} AS "s0" WHERE ("s0"."customer_id" = "s1"."id")) AS "t1") AS "t0"'
        ' ORDER BY "t0"."c1" DESC LIMIT 3) AS "e0") AS "g0" ON TRUE'
    ),
}
# The staged-capture fixture has its own checked-arithmetic and static
# range-refusal witness below.
NESTED_SHAPES = frozenset(SHAPES) - {*POSTGRES_REFUSED, "staged_capture"}


def _wired(tmp_path: Path, shape: str):
    """One admitted nested program's VERIFIED outcome and its artifact."""
    files = sources(shape) if shape in NESTED_SHAPES else collecting.wired_files(shape)
    document = collecting.contract(library=shape == "imported_source")
    outcome = collecting.wired_outcome(tmp_path / shape, files, document)
    artifact: Any = outcome.artifact
    assert outcome.status == "VERIFIED" and artifact is not None, outcome.blockers
    return outcome, artifact


def test_an_admitted_collect_read_keeps_the_flat_refusals_of_its_statement(
    tmp_path: Path,
) -> None:
    assert set(EXPECTED_WIRED) == {*NESTED_SHAPES, *collecting.WIRED, "imported_source"}
    files = sources("staged_capture")
    outcome = collecting.wired_outcome(
        tmp_path / "staged", files, collecting.contract()
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert verify_project_sql_emission(
        outcome.artifact, outcome.artifact.request
    ).verified
    assert b"target_checked_signed64_narrowing" in serialize_project_sql_emission(
        outcome
    )
    files = {
        path: text.replace(
            "let doubled = id * 2", "let doubled = 9223372036854775807 + 1"
        )
        for path, text in files.items()
    }
    outcome = collecting.wired_outcome(
        tmp_path / "outside", files, collecting.contract()
    )
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1002", "arithmetic_outside_physical_range")
    ]


@pytest.mark.parametrize("shape", sorted(EXPECTED_WIRED))
def test_postgres_emits_each_collect_read_of_the_selected_query(
    tmp_path: Path, shape: str
) -> None:
    outcome, artifact = _wired(tmp_path, shape)
    sql = artifact.rendered.sql.decode()
    assert sql == EXPECTED_WIRED[shape]
    assert verify_project_sql_emission(artifact, artifact.request).verified
    reads = len(artifact.request.plan.collects)
    assert reads == (2 if shape == "parallel" else 1)
    assert sql.count(' LEFT JOIN LATERAL (SELECT COUNT(*) AS "n", ') == reads
    assert sql.count(" ON TRUE") == reads and "COALESCE" not in sql
    document = serialize_project_sql_emission(outcome).decode()
    assert not any(sentinel in document for sentinel in SENTINELS)
    columns = json.loads(document)["columns"]
    assert [c["logical_type"]["kind"] for c in columns].count("collection") == reads


def test_the_public_document_describes_a_nested_column_and_its_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = project(tmp_path / "top_k", sources("top_k"))
    (root / "contract.json").write_text(collecting.contract(), encoding="utf-8")
    code, out, _ = _emit(root, "postgres", capsys, "--format", "json")
    document = json.loads(out)
    assert (code, document["status"]) == (0, "VERIFIED")
    assert document["format"] == "pietto.sql-emission.v1"
    flat, nested_column = document["columns"]
    assert flat["logical_type"]["kind"] == "builtin"
    assert flat["correspondence"]["sql_symbol"] == 1

    def ref(kind, position):
        return {"kind": kind, "position": position}

    def element(ordinal, label):
        builtin = {"kind": "builtin", "name": "Int", "parameters": None}
        return {
            "ordinal": ordinal,
            "label": label,
            "logical_type": builtin,
            "nullable": False,
        }

    # Q1 (a): one `collection` entry; its count and arrays are physical
    # statement columns 2, 3 and 4 under the field's and children's labels.
    assert nested_column == {
        "ordinal": 1,
        "label": "recent_orders",
        "logical_type": {
            "kind": "collection",
            "name": None,
            "parameters": None,
            "element": [element(0, "id"), element(1, "total")],
        },
        "nullable": False,
        "representation": {
            "carrier": "pg_column_arrays_v1",
            "columns": [
                {"role": "count", "sql_symbol": 2},
                {
                    "role": "field",
                    "child": 0,
                    "storage": {"kind": "pg_int8"},
                    "sql_symbol": 3,
                },
                {
                    "role": "field",
                    "child": 1,
                    "storage": {"kind": "pg_int8"},
                    "sql_symbol": 4,
                },
            ],
        },
        "correspondence": {
            "collect": ref("collect", 0),
            "use": ref("expression_block_use", 0),
            "producer": ref("definition", 2),
            "children": [ref("export", 0), ref("export", 1)],
            "export": ref("export", 3),
            "sql_symbol": 2,
        },
    }
    assert document["sql"].startswith(
        'SELECT "s1"."id" AS "id", "g0"."n" AS "recent_orders", '
        '"g0"."a0" AS "id", "g0"."a1" AS "total" FROM '
    )
    # R27 owns the three COLLECTION demands and every generated Collect part.
    collect_rules = [
        (item["denominator"], item["kind"], item["subject"])
        for item in document["requirements"]
        if item["rule"] == "R27"
    ]
    assert collect_rules == [
        ("original", "collection", ref("collect", 0)),
        ("original", "collection", ref("collect", 0)),
        ("original", "collection", ref("export", 3)),
        ("generated", "collect_lateral", ref("collect", 0)),
        ("generated", "collect_count", ref("export", 3)),
        ("generated", "collect_array", ref("export", 0)),
        ("generated", "collect_array", ref("export", 1)),
        ("generated", "collect_ordinal", ref("relation_order", 0)),
    ]
    assert all(
        item["kind"] != "collection" or item["rule"] == "R27"
        for item in document["requirements"]
    )
    roles = {item["role"] for item in document["ranges"]}
    assert {
        "collect_lateral_open",
        "collect_lateral_close",
        "collect_on_true",
        "collect_count",
        "collect_array",
        "collect_array_order",
        "collect_scope",
        "collect_reference",
        "collect_carrier_column",
        "ordinal_window",
        "ordinal_column",
    } <= roles
    sql = document["sql"].encode()
    for item in document["ranges"]:
        if item["role"] == "collect_on_true":
            assert sql[item["start"] : item["end"]] == b" ON TRUE"
        if item["role"] == "collect_count" and item["kind"] == "syntax":
            assert sql[item["start"] : item["end"]] == b"COUNT(*)"

    code, out, text = _emit(root, "postgres", capsys, "--format", "text")
    assert code == 0 and text == ""
    lines = out.splitlines()
    assert lines[0] == "pietto.sql-emission.v1 VERIFIED"
    start = lines.index("columns (2):")
    assert json.loads(lines[start + 2].strip()) == nested_column
    assert not any(sentinel in out for sentinel in SENTINELS)


TRAILING_FLAT = """query result:
    let ks:
        from orders
        select:
            id
            total
        order by:
            total desc
            id
    from rows
    select:
        id
        a = collect ks
        other
"""


@pytest.mark.parametrize("tail", ["", "    order by id desc\n    limit 4\n"])
def test_a_flat_column_after_a_nested_field_keeps_its_logical_sql_symbol(
    tmp_path: Path, tail: str
) -> None:
    files = {"main.pietto": HEAD.format(target="postgres") + TRAILING_FLAT + tail}
    outcome = collecting.wired_outcome(tmp_path / "p", files, collecting.contract())
    assert outcome.status == "VERIFIED", outcome.blockers
    document = json.loads(serialize_project_sql_emission(outcome))
    # The JSON v2 rule: every correspondence.sql_symbol is logical, and a flat
    # column's statement column adds the F of each nested field before it.
    statement, offset = [], 0
    for column in document["columns"]:
        physical = column["representation"].get("columns")
        if physical is None:
            statement.append(column["correspondence"]["sql_symbol"] + offset)
        else:
            statement.extend(item["sql_symbol"] for item in physical)
            offset += len(column["logical_type"]["element"])
    assert [c["correspondence"]["sql_symbol"] for c in document["columns"]] == [
        1,
        2,
        3,
    ]
    assert statement == [1, 2, 3, 4, 5]
    select_list = document["sql"].rsplit(") SELECT ", 1)[1].split(" FROM ", 1)[0]
    assert re.findall(r' AS "(\w+)"', select_list) == [
        "id",
        "a",
        "id",
        "total",
        "other",
    ]


def test_a_distinct_let_is_wrapped_by_its_ordinal_at_the_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = project(tmp_path / "distinct", sources("distinct_producer"))
    (root / "contract.json").write_text(collecting.contract(), encoding="utf-8")
    _, out, _ = _emit(root, "postgres", capsys, "--format", "json")
    document = json.loads(out)
    roles = [item["role"] for item in document["ranges"]]
    assert roles.count("distinct_wrapper_open") == roles.count("distinct_wrapper_close")
    assert roles.count("distinct_wrapper_open") == 1
    kinds = [
        item["kind"]
        for item in document["requirements"]
        if item["kind"].startswith("collect_")
    ]
    # The ordinal belongs to the wrapper, so it follows the arrays.
    assert kinds == ["collect_lateral", "collect_count", "collect_array"] + [
        "collect_ordinal"
    ]


def test_mysql_refuses_a_captured_collect_beside_a_table_function_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = sources("top_k", "mysql")
    files["main.pietto"] = files["main.pietto"].replace(
        "    from rows\n    select:\n        id\n        recent_orders",
        "    from rows\n    where exists series\n    select:\n        id\n"
        "        recent_orders",
    ) + (
        "query series:\n    from generate_series(1, 3, 1) as n\n    select:\n        n\n"
    )
    root = project(tmp_path / "mysql", files)
    (root / "contract.json").write_text(collecting.contract("mysql"), encoding="utf-8")
    _, out, _ = _emit(root, "mysql", capsys, "--format", "json")
    document = json.loads(out)
    # F-2: never also the correlated ORDER/LIMIT read refusal at the Collect.
    assert [item["subject"]["detail"] for item in document["blockers"]] == [
        "table_function_not_admitted_on_target",
        "collect_not_admitted_on_target",
    ]


# A captured Top-K let with a literal in its WHERE and SELECT under a parent
# with its own WHERE literal and two literal columns around the Collect.
BIND_SAFE = """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id and orders.total > 5
        select:
            id
            k = 11
        order by created_at desc, id
        limit 2
    from rows
    where rows.id > 1
    select:
        id
        tag = 3
        recent_orders = collect recent
        z = 4
"""
# Header parameters read by the parent's WHERE and column and by the let.
HEADER = """query result(cutoff: Int, floor: Int):
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id and orders.total > cutoff
        select:
            id
            total
        order by created_at desc, id
        limit 2
    from rows
    where rows.id > floor
    select:
        id
        bump = id + floor
        recent_orders = collect recent
"""


def _placeholders(sql: str) -> list[int]:
    return [int(item) for item in re.findall(r"\$(\d+)", sql)]


def test_a_collected_lets_native_occurrences_follow_the_rendered_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {"main.pietto": HEAD.format(target="postgres") + BIND_SAFE}
    root = project(tmp_path / "bind-safe", files)
    document = collecting.contract(parameters=True)
    (root / "contract.json").write_text(document, encoding="utf-8")
    _, out, _ = _emit(
        root, "postgres", capsys, "--format", "json", "--literal-policy", "bind-safe"
    )
    emitted = json.loads(out)
    assert emitted["status"] == "VERIFIED"
    sql = emitted["sql"]
    # H10: the let's own literals render inside the lateral, after the
    # parent's SELECT list, and are numbered there.
    assert _placeholders(sql) == [1, 2, 3, 4, 5]
    assert sql.index("$3") < sql.index(" LEFT JOIN LATERAL (") < sql.index("$4")
    values = {item["slot"]: item["value"] for item in emitted["fixed_values"]}
    uses = emitted["parameter_uses"]
    assert [values[use["slot"]] for use in uses] == ["1", "3", "4", "11", "5"]
    assert [use["server_index"] for use in uses] == [1, 2, 3, 4, 5]
    starts = [use["range"]["start"] for use in uses]
    assert starts == sorted(starts)
    assert all(
        sql.encode()[use["range"]["start"] : use["range"]["end"]].decode()
        == f"${use['server_index']}"
        for use in uses
    )


def test_a_collected_let_reads_header_parameters_in_rendered_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {"main.pietto": HEAD.format(target="postgres") + HEADER}
    root = project(tmp_path / "header", files)
    document = collecting.contract(parameters=True)
    (root / "contract.json").write_text(document, encoding="utf-8")
    _, out, _ = _emit(root, "postgres", capsys, "--format", "json")
    emitted = json.loads(out)
    assert emitted["format"] == "pietto.sql-emission.v2"
    sql = emitted["sql"]
    # floor (parameter 1) is read twice before the lateral, cutoff inside it.
    assert _placeholders(sql) == [1, 1, 2]
    assert sql.index("$1") < sql.index(" LEFT JOIN LATERAL (") < sql.index("$2")
    assert [
        (use["owner"], use["server_index"]) for use in emitted["parameter_uses"]
    ] == [
        ({"kind": "parameter", "parameter": 1}, 1),
        ({"kind": "parameter", "parameter": 1}, 1),
        ({"kind": "parameter", "parameter": 0}, 2),
    ]
    reads = {item["name"]: len(item["reads"]) for item in emitted["parameters"]}
    assert reads == {"cutoff": 1, "floor": 2}
    # `id + floor` waits for both: the let's read reaches the relation.
    (obligation,) = emitted["binding_obligations"]
    assert (obligation["kind"], obligation["parameters"]) == (
        "int_range_representable",
        [0, 1],
    )


def _limited(monkeypatch: pytest.MonkeyPatch, **changes: int) -> None:
    original = emission_ast.resource_limits
    monkeypatch.setattr(
        emission_ast,
        "resource_limits",
        lambda request: {**original(request), **changes},
    )


def test_physical_columns_and_lateral_nodes_count_against_the_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, flat = _wired(tmp_path / "unlimited", "closed")
    parent = flat.ast.bodies[-1]
    (column,) = (c for c in parent.columns if type(c) is nested.CollectColumn)
    # id, then the count and two arrays; the terminal: two columns and its
    # ordinal; the lateral: join, SELECT, FROM, alias, ON, count, 3 per array.
    assert (len(parent.columns), nested.physical_width(parent)) == (2, 4)
    assert nested.physical_width(column.lateral.target.producer) == 3
    assert nested.node_count(column.lateral) == 12
    for columns, status in ((4, "VERIFIED"), (3, "BLOCKED")):
        with monkeypatch.context() as patched:
            _limited(patched, columns=columns)
            outcome = collecting.wired_outcome(
                tmp_path / f"columns-{columns}",
                sources("closed"),
                collecting.contract(),
            )
        assert outcome.status == status
        if status == "BLOCKED":
            # Logically 2 columns, physically 4: PostgreSQL counts the latter.
            assert [(b.code, b.detail) for b in outcome.blockers] == [
                ("PIE-B1007", "generated_structure_limit")
            ]
    for nodes, status in (
        (flat.ast.nodes, "VERIFIED"),
        (flat.ast.nodes - 1, "BLOCKED"),
    ):
        with monkeypatch.context() as patched:
            _limited(patched, nodes=nodes)
            outcome = collecting.wired_outcome(
                tmp_path / f"nodes-{nodes}", sources("closed"), collecting.contract()
            )
        assert outcome.status == status


def test_executing_a_collect_read_is_refused_before_any_connection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = project(tmp_path / "compile", sources("top_k"))
    (root / "contract.json").write_text(collecting.contract(), encoding="utf-8")
    code, _, _ = _emit(root, "postgres", capsys, "--format", "json")
    assert code == 0
    drivers = ("psycopg", "mysql.connector", "adbc_driver_manager")
    before = set(sys.modules)
    with pytest.raises(execution.RequestRejected) as error:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect="postgres",
            emission_contract="contract.json",
        )
    assert error.value.code == "PIE-R1004"
    assert error.value.detail == "NESTED_UNAVAILABLE"
    assert not any(name.startswith(drivers) for name in set(sys.modules) - before)


def test_a_verified_collect_artifact_is_inspected_and_has_its_output(
    tmp_path: Path,
) -> None:
    from pietto._project.project_result_output import (
        NestedOutputColumn,
        prepare_output,
    )
    from pietto._project.project_sql_emission_inspection import (
        inspect_project_sql_emission,
    )

    _, artifact = _wired(tmp_path, "parallel")
    inspection = inspect_project_sql_emission(artifact, artifact.request)
    assert inspection.artifact is artifact
    # S10 opened the output view: each sibling Collect read is its own carrier
    # descriptor, its 1+F statement columns in order.
    output = prepare_output(artifact)
    assert [
        (type(c) is NestedOutputColumn, c.label, getattr(c, "aliases", None))
        for c in output.columns
    ] == [
        (False, "id", None),
        (True, "xs", ("xs", "id")),
        (True, "ys", ("ys", "id", "total")),
    ]


def _swap(units, old, new):
    return tuple(new if unit is old else unit for unit in units)


def _rebuilt(query, units):
    if type(query) is SQLRowQuery:
        return replace(query, bodies=units)
    return replace(query, units=units)


def _corrupted_artifact(artifact, corruption):
    """A VERIFIED nested artifact with one change its builder never makes."""
    query = artifact.ast
    units = collecting.units(query)
    parent = next(u for u in units if getattr(u, "laterals", ()))
    column = next(c for c in parent.columns if type(c) is nested.CollectColumn)
    lateral = column.lateral
    if corruption == "lateral_dropped":
        changed = replace(parent, laterals=())
        return replace(artifact, ast=_rebuilt(query, _swap(units, parent, changed)))
    if corruption == "arrays_swapped":
        swapped = replace(column, lateral=replace(lateral, arrays=lateral.arrays[::-1]))
        changed = replace(
            parent,
            columns=tuple(swapped if c is column else c for c in parent.columns),
            laterals=(swapped.lateral,),
        )
        return replace(artifact, ast=_rebuilt(query, _swap(units, parent, changed)))
    if corruption == "ordinal_dropped":
        terminal = lateral.target.producer
        bare = replace(terminal, ordinal=None)
        moved = replace(
            column,
            lateral=replace(lateral, target=replace(lateral.target, producer=bare)),
        )
        changed = replace(
            parent,
            columns=tuple(moved if c is column else c for c in parent.columns),
            laterals=(moved.lateral,),
        )
        rebuilt = _swap(_swap(units, terminal, bare), parent, changed)
        return replace(artifact, ast=_rebuilt(query, rebuilt))
    if corruption == "group_flattened":
        result = units[-1]
        group = next(
            c for c in result.columns if type(c) is resulting.ResultGroupColumn
        )
        flat = resulting.ResultColumn(
            *(getattr(group, name) for name in resulting.ResultColumn.__slots__)
        )
        changed = replace(
            result, columns=tuple(flat if c is group else c for c in result.columns)
        )
        return replace(artifact, ast=_rebuilt(query, _swap(units, result, changed)))
    if corruption == "requirement_dropped":
        return replace(
            artifact,
            generated_requirements=tuple(
                item
                for item in artifact.generated_requirements
                if item.kind != "collect_lateral"
            ),
        )
    assert corruption == "collection_rule"
    return replace(
        artifact,
        original_requirements=tuple(
            replace(item, rule="R02")
            if item.entry.family.value == "collection"
            else item
            for item in artifact.original_requirements
        ),
    )


ARTIFACT_CORRUPTIONS = {
    "lateral_dropped": ("closed", "plan_ast_correspondence"),
    "arrays_swapped": ("closed", "plan_ast_correspondence"),
    "ordinal_dropped": ("closed", "plan_ast_correspondence"),
    "group_flattened": ("ordered_parent", "plan_ast_correspondence"),
    "requirement_dropped": ("top_k", "requirement_denominators"),
    "collection_rule": ("top_k", "requirement_denominators"),
}


@pytest.mark.parametrize("corruption", sorted(ARTIFACT_CORRUPTIONS))
def test_a_corrupted_nested_artifact_is_never_published(
    tmp_path: Path, corruption: str
) -> None:
    shape, issue = ARTIFACT_CORRUPTIONS[corruption]
    outcome, artifact = _wired(tmp_path, shape)
    changed = _corrupted_artifact(artifact, corruption)
    issues = verify_project_sql_emission(changed, changed.request).issues
    assert issue in issues
    forged = replace(outcome, artifact=changed)
    published = json.loads(serialize_project_sql_emission(forged))
    assert published["status"] == "BLOCKED"
    assert [
        (item["code"], item["subject"]["detail"]) for item in published["blockers"]
    ] == [("PIE-B1008", "artifact_correspondence")]


@pytest.mark.parametrize(
    "name",
    [p.name for p in oracle.programs() if isinstance(p.spec, oracle.Collect)],
)
def test_every_literal_oracle_collect_program_emits_on_postgres(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    # D-T1: the literal oracle's Collect family is S08's emission corpus; its
    # values are compared on a real PostgreSQL by the native run (D71.11).
    program = oracle.program(name)
    root = tmp_path / name
    root.mkdir()
    for path, text in program.files:
        (root / path).write_text(text, encoding="utf-8")
    (root / "contract.json").write_text(collecting.oracle_contract(), encoding="utf-8")
    code, out, _ = _emit(root, "postgres", capsys, "--format", "json")
    document = json.loads(out)
    assert (code, document["status"]) == (0, "VERIFIED"), document["blockers"]
    spec = program.spec
    assert isinstance(spec, oracle.Collect)
    lets = spec.lets
    assert document["sql"].count(" LEFT JOIN LATERAL (") == len(lets)
    nested_columns = [
        c for c in document["columns"] if c["logical_type"]["kind"] == "collection"
    ]
    assert [c["label"] for c in nested_columns] == [let.name for let in lets]
    assert [
        [e["label"] for e in c["logical_type"]["element"]] for c in nested_columns
    ] == [[*let.select, *(("n",) if let.group is not None else ())] for let in lets]
