"""Nested-relation project sources and their verified SQL-plan roots."""

from __future__ import annotations

import json
from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan

HEAD = """shape Row:
    id: Int
    other: Int | None
shape Order:
    id: Int
    customer_id: Int
    total: Int
    created_at: Int
source rows: Row = {target}.table("rows")
source orders: Order = {target}.table("orders")
"""

# A closed let of the parent, collected at main.pietto line 20, column 18.
CLOSED = """query result:
    let children:
        from rows
        select id, other
        order by:
            id
    from rows
    select:
        id
        nested = collect children
"""
# A captured Top-K let: its ORDER BY reads `created_at`, which it does not
# output, and its LIMIT applies per parent row (INPUT checkpoint).
TOP_K = """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            id
            total
        order by created_at desc, id
        limit 2
    from rows
    select:
        id
        recent_orders = collect recent
"""
# A JOIN parent whose captured let reads both JOIN inputs (JOINED checkpoint).
JOINED_CAPTURE = """query result:
    let matched:
        capture rows
        capture peer
        from orders
        where orders.customer_id == rows.id and orders.id == peer.id
        select:
            id
        order by id
    let peer = rows
    from rows
    inner join peer on rows.id == peer.id
    select:
        id = rows.id
        matched_orders = collect matched
"""
JOINED_PARENT = """query result:
    let children:
        from rows
        select id
        order by id
    let peer = rows
    from rows
    inner join peer on rows.id == peer.id
    select:
        id = rows.id
        nested = collect children
"""
# Two independent Collect reads of one parent row, at lines 23 and 24,
# column 14.
PARALLEL = """query result:
    let a:
        from rows
        select id
        order by id
    let b:
        from orders
        select id, total
        order by id
    from rows
    select:
        id
        xs = collect a
        ys = collect b
"""
# The parent itself ends in ORDER BY and LIMIT.
ORDERED_PARENT = """query result:
    let children:
        from rows
        select id
        order by id
    from rows
    select:
        id
        nested = collect children
    order by id
    limit 5
"""
# A window and QUALIFY stage before the PROJECTION block that reads it.
WINDOWED = """query result:
    let children:
        from rows
        select id
        order by id
    let peer = rows
    from rows
    inner join peer on rows.id == peer.id
    select:
        rows.id
        r = row_number() window(order by rows.id)
        nested = collect children
    qualify:
        r == 1
"""
# A captured read after LET and WHERE stages: its capture ports are the
# PROJECTION block's input ports of the parent's FROM row.
STAGED_CAPTURE = """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            id
        order by id
    from rows
    let doubled = id * 2
    where id > 0
    select:
        id
        recent_orders = collect recent
"""
# Producers whose completion rebuilds their row, collected at line 20 and at
# line 23, column 18.
DISTINCT_PRODUCER = """query result:
    let customers:
        from orders
        select distinct:
            customer_id
        order by customer_id
    from rows
    select:
        id
        nested = collect customers
"""
QUALIFY_PRODUCER = """query result:
    let firsts:
        from orders
        select:
            id
            r = row_number() window(order by id)
        qualify:
            r == 1
        order by id
    from rows
    select:
        id
        nested = collect firsts
"""
PARENT = """query parent:
    let children:
        from rows
        select id
        order by id
    from rows
    select:
        id
        nested = collect children
"""
# Flat readers of a parent: they output scalars only; the Collect read is the
# parent's own (line 19, column 18).
READER = PARENT + "query result:\n    from parent\n    select id\n"
EXISTS_READER = (
    PARENT + "query result:\n    from rows\n    where exists parent\n    select id\n"
)
SCALAR_READER = (
    PARENT
    + "query result:\n    from rows\n    select:\n        id\n"
    + "        top = scalar parent.id\n"
)

SHAPES = {
    "closed": CLOSED,
    "top_k": TOP_K,
    "joined_capture": JOINED_CAPTURE,
    "joined_parent": JOINED_PARENT,
    "parallel": PARALLEL,
    "ordered_parent": ORDERED_PARENT,
    "windowed": WINDOWED,
    "staged_capture": STAGED_CAPTURE,
    "distinct_producer": DISTINCT_PRODUCER,
    "qualify_producer": QUALIFY_PRODUCER,
    "reader": READER,
    "exists_reader": EXISTS_READER,
    "scalar_reader": SCALAR_READER,
}


# A parent whose nested field an Unnest reads: its Collect read is at line
# 21, column 18, and a reader's Unnest let at line 24, column 5.
UNNEST_PARENT = """query parent:
    let recent:
        from orders
        select:
            id
            total
        order by id
    from rows
    select:
        id
        nested = collect recent
"""


def _expanded(*lines: str) -> str:
    return UNNEST_PARENT + "query result:\n" + "".join(f"    {x}\n" for x in lines)


_STD = ("from parent", "let o = unnest(parent.nested)")
_OUT = ("select:", "    id = parent.id", "    total = o.total")
UNNEST_SHAPES = {
    "unnest_cross": _expanded(*_STD, "cross join o", *_OUT),
    "unnest_inner": _expanded(*_STD, "inner join o on o.total > 10", *_OUT),
    "unnest_left": _expanded(*_STD, "left join o on True", *_OUT),
    "unnest_left_where": _expanded(
        *_STD, "left join o on True", "where o.total > 10", *_OUT
    ),
    "unnest_left_on_parent": _expanded(
        *_STD, "left join o on o.total > parent.id", *_OUT
    ),
    "unnest_left_on_match": _expanded(*_STD, "left join o on o.total > 10", *_OUT),
    "unnest_ordered": _expanded(
        *_STD, "cross join o", *_OUT, "order by total desc", "limit 3"
    ),
    # The Unnest let reads a FROM alias, at line 25.
    "unnest_alias": _expanded(
        "let p = parent",
        "from p",
        "let o = unnest(p.nested)",
        "cross join o",
        "select:",
        "    id = p.id",
        "    total = o.total",
    ),
    # The Unnest reads a JOIN binding that may null-extend: its JOIN is the
    # second, its let at line 26.
    "unnest_left_joined_parent": _expanded(
        "from rows",
        "let p = parent",
        "left join p on rows.id == p.id",
        "let o = unnest(p.nested)",
        "left join o on True",
        "select:",
        "    id = rows.id",
        "    total = o.total",
    ),
    "unnest_join_binding": _expanded(
        "from rows",
        "let p = parent",
        "inner join p on rows.id == p.id",
        "let o = unnest(p.nested)",
        "cross join o",
        "select:",
        "    id = rows.id",
        "    total = o.total",
    ),
    "unnest_cross_joined_parent": _expanded(
        "from rows",
        "let p = parent",
        "cross join p",
        "let o = unnest(p.nested)",
        "cross join o",
        "select:",
        "    id = rows.id",
        "    total = o.total",
    ),
    # A table function, an Unnest and their declaration share its body's
    # positions; the Unnest let is at line 25.
    "unnest_beside_series": _expanded(
        "from generate_series(1, 3, 1) as g",
        "cross join parent",
        "let o = unnest(parent.nested)",
        "cross join o",
        "select:",
        "    g",
        "    total = o.total",
    ),
    # A let that captures the Unnest's own binding, read by `exists` in the
    # same body; the Unnest let is at line 30.
    "unnest_captured_exists": _expanded(
        "let side:",
        "    capture parent",
        "    from orders",
        "    where orders.customer_id == parent.id",
        "    select:",
        "        id",
        "from parent",
        "let o = unnest(parent.nested)",
        "cross join o",
        "where exists side",
        "select:",
        "    id = parent.id",
        "    total = o.total",
    ),
    # Two declarations each with an Unnest at the same let position: the
    # reader's JOIN of `other` follows its own Unnest JOIN; the Unnest lets
    # are at lines 24 and 30.
    "unnest_two_bodies": UNNEST_PARENT
    + "query other:\n    from parent\n    let o = unnest(parent.nested)\n"
    + "    cross join o\n    select:\n        total = o.total\n"
    + "query result:\n    from parent\n    let o = unnest(parent.nested)\n"
    + "    cross join o\n    cross join other\n    select:\n"
    + "        a = o.total\n        b = other.total\n",
    # The language reference example, its reader named `result`: its Collect
    # read is at line 20, column 25, and its Unnest let at line 23.
    "unnest_language": """query customers_with_orders:
    let recent:
        from orders
        select:
            id
        order by id
    from orders
    select:
        customer_id
        recent_orders = collect recent
query result:
    from customers_with_orders
    let o = unnest(customers_with_orders.recent_orders)
    cross join o
    select:
        customer_id
""",
    # An INNER JOIN whose `on` compares a nullable element field narrows it to
    # NON NULL, as for any JOIN input: its Collect read is at line 19, column
    # 18, and its Unnest let at line 22.
    "unnest_inner_nullable": """query parent:
    let kids:
        from rows
        select id, other
        order by id
    from rows
    select:
        id
        nested = collect kids
query result:
    from parent
    let o = unnest(parent.nested)
    inner join o on o.other > 1
    select:
        id = parent.id
        other = o.other
""",
}


def sources(shape: str, target: str = "postgres") -> dict[str, str]:
    """One-module project sources of a named shape."""
    return {
        "main.pietto": HEAD.format(target=target)
        + (SHAPES[shape] if shape in SHAPES else UNNEST_SHAPES[shape])
    }


def imported_sources(target: str = "postgres") -> dict[str, str]:
    """The parent and its collected let in another module than its reader."""
    return {
        "parent.pietto": HEAD.format(target=target)
        + PARENT
        + "export (\n    query parent,\n)\n",
        "main.pietto": 'from "parent.pietto" import (\n    query parent,\n)\n'
        + "query result:\n    from parent\n    select id\n",
    }


def imported_unnest_sources(target: str = "postgres") -> dict[str, str]:
    """An Unnest of an imported parent's nested field, at main.pietto line 6."""
    return {
        "parent.pietto": HEAD.format(target=target)
        + UNNEST_PARENT
        + "export (\n    query parent,\n)\n",
        "main.pietto": 'from "parent.pietto" import (\n    query parent,\n)\n'
        + "query result:\n    from parent\n    let o = unnest(parent.nested)\n"
        + "    cross join o\n    select:\n        total = o.total\n",
    }


def project(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir(parents=True)
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
    return directory


def nested_roots(directory: Path, files: dict[str, str], owner: str = "result"):
    """The completed result, verified IR bundle and selected owner."""
    parsed = check_project_parse_only(project(directory, files))
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert completed.ok, completed.diagnostics
    assert type(completed) is ProjectConcreteCompletedSemanticResult
    checked = verify_project_query_block_ir(build_project_query_block_ir(completed))
    assert checked.verified, checked.issues
    bundle = build_project_query_block_ir_analysis_bundle(checked)
    (selected,) = (
        o
        for o in bundle.root.owners
        if o.definition.name == owner
        and o.let_position is None
        and o.identity.module_path == "main.pietto"
    )
    return completed, bundle, selected


def nested_plan(directory: Path, files: dict[str, str], owner: str = "result"):
    """The VERIFIED plan verification of one nested project's owner."""
    roots = nested_roots(directory, files, owner)
    plan = build_project_sql_plan(*roots)
    assert type(plan) is ProjectSQLPlan, getattr(plan, "blockers", ())
    verification = verify_project_sql_plan(plan, *roots)
    assert verification.verified, verification.issues
    return verification


def emission_contract(target: str, module: str = "main.pietto") -> str:
    """A contract that declares both sources' Int columns."""
    storage = "pg_int8" if target == "postgres" else "my_bigint"

    def source(name, fields):
        return {
            "scan": "relation_rows",
            "selector": {"module": module, "kind": "source", "name": name},
            "relation": {
                "namespace": "public" if target == "postgres" else "phase66",
                "name": name,
            },
            "fields": [
                {
                    "ordinal": i,
                    "name": field,
                    "column": field,
                    "representation": {
                        "storage": {"kind": storage},
                        "nullable": nullable,
                        "domain": {
                            "kind": "int_range",
                            "min": str(-(2**63)),
                            "max": str(2**63 - 1),
                        },
                    },
                }
                for i, (field, nullable) in enumerate(fields)
            ],
            "premises": [
                {"key": key, "scope": "source", "value": True}
                for key in ("row_domain_matches", "read_only_object")
            ],
        }

    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {
                "family": target,
                "release": "18.6" if target == "postgres" else "8.4.12",
            },
            "sources": [
                source("rows", (("id", False), ("other", True))),
                source(
                    "orders",
                    (
                        ("id", False),
                        ("customer_id", False),
                        ("total", False),
                        ("created_at", False),
                    ),
                ),
            ],
            "environment": [
                {
                    "key": "client_encoding",
                    "scope": "statement",
                    "value": "UTF8" if target == "postgres" else "utf8mb4",
                },
                {
                    "key": "operator_environment",
                    "scope": "statement",
                    "value": "builtin_only",
                },
            ],
        }
    )
