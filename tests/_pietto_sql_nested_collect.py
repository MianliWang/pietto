"""Collect SQL emission programs: flat stand-ins and real nested sources.

A Collect is attached by hand to a real flat emission: a real block read's
target (its let's terminal and alias, and a captured let's real capture scope),
a real parent body and the plan's own refs. ``collect_record`` builds the plan's
own ``ProjectSQLCollect`` by keyword. A captured let's record takes the plan
captures its flat read completes, and that read's ref as its own, as a Collect
read's captures name it.

``WIRED`` are real nested `result` queries over S06's two sources; ``contract``
adds the statement premises a generated scope or a placeholder needs, and
``oracle_contract`` declares the literal oracle's seed tables (D-T1).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any

import _pietto_execution_nested_oracle as oracle
from _pietto_plan_nested import HEAD, emission_contract, nested_plan
import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_nested as nested
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission import emit_project_sql
from pietto._project.project_sql_emission_ast import RowBody, SQLRowQuery, SQLSymbol
from pietto._project.project_sql_emission_rendering import (
    render_join_sql,
    render_row_sql,
)
from pietto._project.project_sql_plan_nested import ProjectSQLCollect


@dataclass(frozen=True, slots=True, eq=False)
class _CollectRef:
    """A COLLECT ref stand-in: compared by identity like every plan ref."""

    position: int


def collect_record(**fields) -> ProjectSQLCollect:
    return ProjectSQLCollect(**fields)


# A closed let ordered by a hidden NULLABLE key, then its output, read by `in`.
CLOSED = """query result:
    let top:
        from rhs
        select:
            id
        order by:
            key{direction}
            id
        limit 2
    from lhs
    where lhs.id in top
    select:
        a = lhs.id
        b = lhs.key
"""
# A captured Top-K let ordered by its hidden key, read by `scalar`.
CAPTURED = """query result:
    let top:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
        order by:
            key desc
        limit 2
    from lhs
    select:
        a = lhs.id
        k = scalar top.id
"""
DISTINCT = """query result:
    let top:
        from rhs
        select distinct:
            key
        order by:
            key desc
        limit 2
    from lhs
    where lhs.key in top
    select:
        a = lhs.id
        b = lhs.key
"""
GROUPED = """query result:
    let top:
        from rhs
        group by:
            key
        select:
            n = count()
        order by:
            n desc
    from lhs
    where lhs.id in top
    select:
        a = lhs.id
        b = lhs.key
"""
# A captured let reading the JOIN's right input, in the JOIN body's SELECT.
JOINED = """query result:
    let top:
        capture r
        from rhs
        where rhs.key == r.key
        select:
            id
        order by:
            id desc
        limit 2
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
    select:
        a = lhs.id
        k = scalar top.id
"""
# A captured let with two capture lines, both completed at its one read.
CAPTURES = """query result:
    let top:
        capture lhs
        capture r
        from rhs
        where rhs.key == lhs.key and rhs.id == r.id
        select:
            id
        order by:
            id desc
        limit 2
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
    select:
        a = lhs.id
        k = scalar top.id
"""
# Two sibling lets, a closed one and a captured one with two outputs.
SIBLINGS = """query result:
    let top:
        from rhs
        select:
            id
        order by:
            id desc
        limit 2
    let low:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
            key
        order by:
            id
    from lhs
    select:
        a = lhs.id
        x = scalar top.id
        y = scalar low.id
"""
# A parent with its own ORDER BY and LIMIT, so its projection is a CTE.
ORDERED_PARENT = """query result:
    let top:
        from rhs
        select:
            id
        order by:
            id desc
        limit 2
    from lhs
    where lhs.id in top
    select:
        a = lhs.id
        b = lhs.key
    order by:
        lhs.id
    limit 3
"""
# A captured two-output let under a parent with its own ORDER BY and LIMIT.
ORDERED_PAIR = """query result:
    let low:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
            key
        order by:
            id
    from lhs
    select:
        a = lhs.id
        y = scalar low.id
    order by:
        lhs.id
    limit 3
"""
# Two closed sibling lets in opposite orders under a parent with its own
# ORDER BY and LIMIT, so its result body carries two groups.
ORDERED_SIBLINGS = """query result:
    let high:
        from rhs
        select:
            id
        order by:
            id desc
        limit 2
    let low:
        from rhs
        select:
            id
        order by:
            id
        limit 2
    from lhs
    select:
        a = lhs.id
        x = scalar high.id
        y = scalar low.id
    order by:
        lhs.id
    limit 3
"""
# A let with DISTINCT and no ORDER: no Collect sequence exists for it.
UNORDERED = """query result:
    let keys:
        from rhs
        select distinct:
            key
    from lhs
    where lhs.key in keys
    select:
        a = lhs.id
"""


def emit(directory: Path, body: str):
    """One PostgreSQL emission of a flat stand-in, literals preserved."""
    item = probe.join_witness("postgres", body)
    checked, outcome = probe.build_case(
        directory, item["source"], item["contract"], item["policy"]
    )
    assert outcome.artifact is not None, outcome
    return checked, outcome.artifact


def units(query) -> tuple[Any, ...]:
    return query.bodies if type(query) is SQLRowQuery else query.units


def block_targets(query) -> dict[int, rows.SQLBlockTarget]:
    """Every realized block read target of the flat query, by use position."""
    found: dict[int, rows.SQLBlockTarget] = {}
    for unit in units(query):
        if type(unit) is not RowBody:
            continue
        values = [getattr(c, "value", None) for c in unit.columns]
        if unit.predicate is not None:
            values.append(unit.predicate.value)
        for value in values:
            for node in () if value is None else rows.value_nodes(value):
                if type(node) is rows.SQLBlockRead:
                    found.setdefault(node.target.use.ref.position, node.target)
    return found


def with_ordinal(request, terminal):
    """The terminal rebuilt as a Collect reads it, by its own builder."""
    rebuilt, problem = resulting.build_result_body(
        request,
        terminal.definition,
        terminal.boundaries,
        terminal.scan.body,
        index=terminal.index,
        final=terminal.final,
        symbol=SQLSymbol,
        inline=terminal.symbol is None,
        ordinal=True,
    )
    assert problem is None, problem
    return rebuilt


def plan_order_limit(plan, producer):
    """The plan's own ORDER and LIMIT records of one let, LIMIT possibly None."""
    owner = {b.ref: b.definition for b in plan.result_boundaries}
    (order,) = (o for o in plan.orders if owner[o.boundary] is producer)
    limits = tuple(v for v in plan.result_limits if owner[v.boundary] is producer)
    return order, (limits[0] if limits else None)


@dataclass(frozen=True, slots=True, eq=False)
class Collected:
    """A flat query with Collect columns attached, and what built them."""

    request: Any
    query: Any
    parent: Any
    columns: tuple[Any, ...]
    records: tuple[Any, ...]
    orders: tuple[Any, ...]
    limits: tuple[Any, ...]

    def render(self):
        render = render_row_sql if type(self.query) is SQLRowQuery else render_join_sql
        return render(self.query)


def collect(artifact, reads: dict[int, int]) -> Collected:
    """Replace parent column ``position`` by a Collect of the let that block use
    ``reads[position]`` reads, as the realized parent would carry it."""
    request = artifact.request
    plan = request.plan
    query = artifact.ast
    (parent,) = (
        unit
        for unit in units(query)
        if type(unit) is RowBody
        and unit.block.kind.value == "projection"
        and unit.definition.original.entry.owner is plan.scope.selected_owner
    )
    targets = block_targets(query)
    definitions = {d.ref: d for d in plan.bindings.definitions}
    replaced: dict[int, Any] = {}
    columns = list(parent.columns)
    records, orders, limits = [], [], []
    for index, (position, use) in enumerate(sorted(reads.items())):
        target = targets[use]
        terminal = target.producer
        if terminal.distinct is None:
            rebuilt = replaced.setdefault(id(terminal), with_ordinal(request, terminal))
            target = replace(target, producer=rebuilt)
        producer = target.use.producer
        captures = tuple(c for c in plan.captures if c.inner is producer)
        record = collect_record(
            ref=captures[0].read if captures else _CollectRef(index),
            block=parent.block.ref,
            export=parent.definition.original.exports[position].ref,
            use=target.use.ref,
            producer=producer,
            children=tuple(p.ref for p in definitions[producer].exports),
            captures=tuple(c.ref for c in captures),
            semantic=None,
            fact=None,
        )
        column, problem = nested.realize_collect(
            record,
            target,
            export=parent.definition.original.exports[position],
            position=position,
            final=parent.final,
            terminal=parent.terminals[position],
        )
        assert problem is None, problem
        columns[position] = column
        records.append(record)
        order, limit = plan_order_limit(plan, producer)
        orders.append(order)
        limits.append(limit)
    collected = tuple(c for c in columns if type(c) is nested.CollectColumn)
    grafted = replace(
        parent,
        columns=tuple(columns),
        laterals=tuple(c.lateral for c in collected),
    )
    rebuilt_units = []
    for unit in units(query):
        if unit is parent:
            unit = grafted
        elif id(unit) in replaced:
            unit = replaced[id(unit)]
        elif type(unit) is resulting.RowResultBody and unit.scan.body is parent:
            unit, problem = resulting.build_result_body(
                request,
                unit.definition,
                unit.boundaries,
                grafted,
                index=unit.index,
                final=unit.final,
                symbol=SQLSymbol,
            )
            assert problem is None, problem
        rebuilt_units.append(unit)
    if type(query) is SQLRowQuery:
        changed = replace(query, bodies=tuple(rebuilt_units))
    else:
        changed = replace(query, units=tuple(rebuilt_units))
    return Collected(
        request,
        changed,
        grafted,
        collected,
        tuple(records),
        tuple(orders),
        tuple(limits),
    )


def with_column(collected: Collected, column, changed) -> tuple[Any, Any]:
    """The parent body with one Collect column replaced, laterals in step."""
    parent = collected.parent
    columns = tuple(changed if c is column else c for c in parent.columns)
    return replace(
        parent,
        columns=columns,
        laterals=tuple(c.lateral for c in columns if type(c) is nested.CollectColumn),
    ), changed


# Real nested `result` queries beside S06's shapes (`_pietto_plan_nested`).
WIRED = {
    # A closed grouped let ordered by its aggregate output, then its key.
    "grouped": """query result:
    let totals:
        from orders
        group by:
            customer_id
        select:
            customer_id
            n = count()
        order by:
            n desc
            customer_id
    from rows
    select:
        id
        busiest = collect totals
""",
    # A closed Top-K let ordered first by a hidden NULLABLE key.
    **{
        f"nullable_{name}": f"""query result:
    let kids:
        from rows
        select:
            id
        order by:
            other{direction}
            id
        limit 2
    from rows
    select:
        id
        nested = collect kids
"""
        for name, direction in (("asc", ""), ("desc", " desc"))
    },
    # A captured read after the parent's WHERE stage.
    "filtered": """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            total
        order by:
            total desc
    from rows
    where rows.id > 0
    select:
        id
        totals = collect recent
""",
}
# A captured let reading a source another module declares.
LIBRARY = """shape Order:
    id: Int
    customer_id: Int
    total: Int
    created_at: Int
source orders: Order = postgres.table("orders")
export (
    source orders,
)
"""
IMPORTING = """from "lib.pietto" import (
    source orders,
)
shape Row:
    id: Int
    other: Int | None
source rows: Row = postgres.table("rows")
query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            id
        order by:
            id desc
        limit 3
    from rows
    select:
        id
        recent_orders = collect recent
"""


def wired_files(shape: str, target: str = "postgres") -> dict[str, str]:
    """One nested project's files: a `WIRED` shape or the importing one."""
    if shape == "imported_source":
        return {"lib.pietto": LIBRARY, "main.pietto": IMPORTING}
    return {"main.pietto": HEAD.format(target=target) + WIRED[shape]}


def contract(
    target: str = "postgres", *, parameters: bool = False, library: bool = False
) -> str:
    """S06's two-source contract with the statement premises a generated scope
    and, with ``parameters``, a placeholder need; ``library`` selects `orders`
    from lib.pietto."""
    document = json.loads(emission_contract(target))
    if library:
        document["sources"][1]["selector"]["module"] = "lib.pietto"
    postgres = target == "postgres"
    document["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact" if postgres else "lower_case_table_names=0",
        }
    )
    if parameters:
        document["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended" if postgres else "mysql_prepared",
            }
        )
    return json.dumps(document)


def wired_outcome(directory: Path, files: dict[str, str], document: str):
    """The emission outcome of `result` through its real verified plan."""
    return emit_project_sql(nested_plan(directory, files), document.encode())


# The literal oracle's leaf representations on PostgreSQL (default leaves).
_ORACLE_REPRESENTATIONS = {
    "Int": {
        "storage": {"kind": "pg_int8"},
        "domain": {"kind": "int_range", "min": str(-(2**63)), "max": str(2**63 - 1)},
    },
    "Bool": {"storage": {"kind": "pg_bool"}, "domain": {"kind": "bool01"}},
    "Text": {
        "storage": {"kind": "pg_text"},
        "domain": {
            "kind": "text",
            "max_characters": 64,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    },
}


def oracle_contract() -> str:
    """A PostgreSQL contract for the literal oracle's FULL seed tables."""
    tables = oracle.seed("FULL")
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": "postgres", "release": "18.6"},
            "sources": [
                {
                    "scan": "relation_rows",
                    "selector": {
                        "module": "main.pietto",
                        "kind": "source",
                        "name": table.name,
                    },
                    "relation": {"namespace": "public", "name": table.name},
                    "fields": [
                        {
                            "ordinal": ordinal,
                            "name": column.name,
                            "column": column.name,
                            "representation": {
                                "storage": _ORACLE_REPRESENTATIONS[column.kind][
                                    "storage"
                                ],
                                "nullable": column.nullable,
                                "domain": _ORACLE_REPRESENTATIONS[column.kind][
                                    "domain"
                                ],
                            },
                        }
                        for ordinal, column in enumerate(table.columns)
                    ],
                    "premises": [
                        {"key": key, "scope": "source", "value": True}
                        for key in ("row_domain_matches", "read_only_object")
                    ],
                }
                for table in tables.values()
            ],
            "environment": [
                {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
                {
                    "key": "operator_environment",
                    "scope": "statement",
                    "value": "builtin_only",
                },
                {
                    "key": "identifier_case",
                    "scope": "statement",
                    "value": "quoted_exact",
                },
            ],
        }
    )
