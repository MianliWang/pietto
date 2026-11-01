"""Flat stand-in programs and Unnest records for the Unnest SQL node tests.

Until the S06 Unnest plan records land in this tree, an Unnest is grafted by
hand onto a real flat PostgreSQL emission of ``from parent <kind> join o``,
where ``o`` is a captured let. The parent's nested port is S08's Collect of a
real block read of the parent, the JOIN, its inputs, ports and alias are the
flat JOIN's own, and the right input keeps its real binding use. The captured
let is replaced by the Unnest rows. ``unnest_record`` mirrors
``ProjectSQLUnnest`` field for field and is always built by keyword, so its
tests do not change when it becomes the plan's own class.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, replace
from typing import Any

import _pietto_sql_emission as probe
import _pietto_sql_nested_collect as collecting
from pietto._project import project_sql_emission_joins as joining
from pietto._project import project_sql_emission_nested as nested
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_unnest as unnesting
from pietto._project.project_sql_emission_ast import RowBody, SQLSymbol
from pietto._project.project_sql_emission_rendering import render_join_sql
from pietto._project.project_sql_plan_nested import ProjectSQLCollect


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _UnnestRecord:
    """The plan record of one Unnest (S06 record section 5.7)."""

    ref: Any
    join: Any
    input: Any
    definition: Any
    source: Any
    collect: Any
    outputs: tuple[Any, ...]
    semantic: Any


@dataclass(frozen=True, slots=True, eq=False)
class _UnnestRef:
    """An UNNEST ref stand-in: compared by identity like every plan ref."""

    position: int


def unnest_record(**fields) -> _UnnestRecord:
    return _UnnestRecord(**fields)


def _collect_record(**given):
    """S08's Collect record by keyword. Its capture field is never read here,
    so every field not given is None whatever its spelling."""
    names = (item.name for item in dataclasses.fields(ProjectSQLCollect))
    return collecting.collect_record(**({name: None for name in names} | given))


# The parent: a closed Top-K let read by `in`, so its projection is a CTE.
PARENT = """query parent:
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
"""
# The parent's own ORDER BY and LIMIT: the JOIN reads its result body.
ORDERED_PARENT = (
    PARENT
    + """    order by:
        lhs.id
    limit 3
"""
)
# The nested field first.
FIRST_PARENT = """query parent:
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
        b = lhs.key
        a = lhs.id
"""
# Two children, the second a NULLABLE Int.
PAIR_PARENT = """query parent:
    let top:
        from rhs
        select:
            id
            key
        order by:
            id desc
        limit 2
    from lhs
    where exists top
    select:
        a = lhs.id
        b = lhs.key
"""
# Two sibling lets read by scalars, each a nested field of the parent.
SIBLINGS_PARENT = """query parent:
    let top:
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
    from lhs
    select:
        a = lhs.id
        b = scalar top.id
        c = scalar low.id
"""
# The consumer: the captured let `o` reads one parent field and its outputs
# are the children's types, so the flat right input already has their ports.
CONSUMER = """query result:
    let o:
        capture parent
        from rhs
        where rhs.key == parent.{field}
        select:
{outputs}
    from parent
    {join}
    select:
        a = parent.a
        v = o.id
"""
LATER = """query result:
    let o:
        capture parent
        from rhs
        where rhs.key == parent.b
        select:
            id
    from parent
    cross join o
    let r = rhs
    left join r on parent.a == r.id
    select:
        a = parent.a
        v = o.id
        w = r.key
"""
ID = "            id"
# A query parameter read by the second child: its realization is fixed only
# when the parameter is bound. The parent and the captured let are lets of the
# selected query, which alone declares parameters.
PARAMETER = """query result(low: Int):
    let top:
        from rhs
        select:
            id
            y = rhs.id + low
        order by:
            id desc
        limit 2
    let parent:
        from lhs
        where exists top
        select:
            a = lhs.id
            b = lhs.key
    let o:
        capture parent
        from rhs
        where rhs.key == parent.b
        select:
            id
            y = rhs.id + low
    from parent
    cross join o
    select:
        a = parent.a
        v = o.id
"""


def consumer(join: str, *, field: str = "b", outputs: str = ID) -> str:
    return CONSUMER.format(field=field, outputs=outputs, join=join)


# Each stand-in: its program, the parent position of the Unnest source, and
# the Collect reads {parent position: block use position}.
CASES = {
    "cross": (PARENT + consumer("cross join o"), 1, {1: 0}),
    "inner_on": (PARENT + consumer("inner join o on o.id > 1"), 1, {1: 0}),
    "left_on": (PARENT + consumer("left join o on o.id > 1"), 1, {1: 0}),
    "left_true_first": (
        FIRST_PARENT + consumer("left join o on True"),
        0,
        {0: 0},
    ),
    "pair": (
        PAIR_PARENT + consumer("cross join o", outputs=ID + "\n            key"),
        1,
        {1: 0},
    ),
    "ordered_parent": (ORDERED_PARENT + consumer("cross join o"), 1, {1: 0}),
    "later_join": (PARENT + LATER, 1, {1: 0}),
    "siblings": (
        SIBLINGS_PARENT + consumer("cross join o", field="a"),
        1,
        {1: 0, 2: 1},
    ),
    "parameter": (PARAMETER, 1, {1: 0}),
}
# The stand-ins whose contract binds query parameters.
PARAMETERIZED = frozenset({"parameter"})
# Real JOIN records of other kinds, to graft in place of an Unnest JOIN. A
# SEMI JOIN is authored as a tail `any`, so it has no JOIN record to take.
OTHER_JOINS = {
    "right": "right join r on lhs.id == r.id",
    "full": "full join r on lhs.id == r.id",
}
OTHER = """query result:
    from lhs
    let r = rhs
    {join}
    select:
        a = lhs.id
"""


@dataclass(frozen=True, slots=True, eq=False)
class Grafted:
    """A flat JOIN query with one Unnest grafted, and what built it."""

    request: Any
    query: Any
    unit: Any
    unnest: Any
    collects: tuple[Any, ...]
    flat: Any

    def render(self):
        return render_join_sql(self.query)


def _join_bodies(query) -> tuple[Any, ...]:
    return tuple(u for u in query.units if type(u) is joining.JoinBody)


def graft(artifact, *, position: int, reads: dict[int, int], kind=None) -> Grafted:
    """Replace the first JOIN's right input by an Unnest of the parent's nested
    port ``position``; every ``reads`` position becomes a Collect group."""
    request = artifact.request
    plan = request.plan
    query = artifact.ast
    ports = {port.ref: port for port in plan.join_ports}
    flat = _join_bodies(query)[0]
    left, right = flat.inputs
    producer = left.producer
    parent = (
        producer.scan.body if type(producer) is resulting.RowResultBody else producer
    )
    assert type(parent) is RowBody and not parent.final
    targets = collecting.block_targets(query)
    definitions = {d.ref: d for d in plan.bindings.definitions}
    replaced: dict[int, Any] = {}
    columns = list(parent.columns)
    collects = {}
    for index, (at, use) in enumerate(sorted(reads.items())):
        target = targets[use]
        terminal = target.producer
        rebuilt = replaced.setdefault(
            id(terminal), collecting.with_ordinal(request, terminal)
        )
        target = replace(target, producer=rebuilt)
        produced = target.use.producer
        export = parent.definition.original.exports[at]
        record = _collect_record(
            ref=collecting._CollectRef(index),
            block=parent.block.ref,
            export=export.ref,
            use=target.use.ref,
            producer=produced,
            children=tuple(p.ref for p in definitions[produced].exports),
        )
        column, problem = nested.realize_collect(
            record,
            target,
            export=export,
            position=at,
            final=False,
            terminal=parent.terminals[at],
        )
        assert problem is None, problem
        columns[at] = column
        collects[at] = record
    grafted = replace(
        parent,
        columns=tuple(columns),
        laterals=tuple(c.lateral for c in columns if type(c) is nested.CollectColumn),
    )
    replaced[id(parent)] = grafted
    if type(producer) is resulting.RowResultBody:
        result, problem = resulting.build_result_body(
            request,
            producer.definition,
            producer.boundaries,
            grafted,
            index=producer.index,
            final=producer.final,
            symbol=SQLSymbol,
        )
        assert problem is None, problem
        replaced[id(producer)] = result
    producer = replaced[id(producer)]
    entries = []
    for at, column in enumerate(left.columns):
        if at in reads:
            column, problem = unnesting.nested_read(
                producer.columns[at],
                position=at,
                port=ports[left.ports[at]],
                scope=left.symbol,
            )
            assert problem is None, problem
        entries.append(column)
    left = replace(left, producer=producer, columns=tuple(entries))
    split = len(left.ports)
    record = unnest_record(
        ref=_UnnestRef(0),
        join=flat.join.ref,
        input=right.original.ref,
        definition=None,
        source=left.ports[position],
        collect=collects[position].ref,
        outputs=tuple(flat.join.outputs[split:]),
        semantic=None,
    )
    item, problem = unnesting.realize_unnest(
        record,
        left,
        kind=flat.join.kind if kind is None else kind,
        terminals=tuple(binding.terminal.ref for binding in right.use.bindings),
    )
    assert item is not None, problem
    elements = []
    for j, element in enumerate(item.columns):
        read = replace(element.column, position=j, name=f"c{j}", scope=right.symbol)
        realization, problem = joining.port_realization(
            ports[right.ports[j]], read, outer=False
        )
        assert problem is None, problem
        elements.append(replace(read, realization=realization))
    right = replace(right, producer=item, columns=tuple(elements))
    carriers = (*left.ports, *right.ports)
    rejected = joining.null_rejected_ports(flat.join, flat.equalities, flat.predicate)
    published = []
    for at, reference in enumerate(flat.join.outputs):
        port = ports[reference]
        if at in reads:
            published.append(unnesting.WithheldPort(at, port))
            continue
        if at < split:
            published.append(flat.columns[at])
            continue
        read = right.columns[at - split]
        realization, problem = joining.port_realization(
            port, read, outer=True, proved=carriers[at] in rejected
        )
        assert problem is None, problem
        label = f"c{at}"
        published.append(
            joining.JoinColumn(
                at,
                port,
                ports[carriers[at]],
                label,
                flat.columns[at].symbol,
                replace(
                    read,
                    position=at,
                    name=label,
                    terminal=port.ref,
                    realization=realization,
                    scope=None,
                ),
                read.scope,
                read,
            )
        )
    unit = replace(
        flat,
        inputs=(left, right),
        columns=tuple(published),
        cte_columns=_published_names(flat, published),
    )
    replaced[id(flat)] = unit
    units = [replaced.get(id(u), u) for u in query.units]
    # A later JOIN reads the Unnest JOIN by port position: the same positions
    # stay withheld in its left input and its own published ports.
    for index, later in enumerate(units):
        if type(later) is not joining.JoinBody or later is unit:
            continue
        predecessor = replaced.get(id(later.inputs[0].producer))
        if predecessor is None:
            continue
        held = {
            c.position for c in predecessor.columns if type(c) is unnesting.WithheldPort
        }
        before = later.inputs[0]
        entries = tuple(
            unnesting.WithheldPort(at, ports[before.ports[at]]) if at in held else c
            for at, c in enumerate(before.columns)
        )
        changed = tuple(
            unnesting.WithheldPort(at, c.port) if at in held else c
            for at, c in enumerate(later.columns)
        )
        units[index] = replaced[id(later)] = replace(
            later,
            inputs=(
                replace(before, producer=predecessor, columns=entries),
                later.inputs[1],
            ),
            columns=changed,
            cte_columns=_published_names(later, changed),
        )
    final = units[-1]
    if hasattr(final.scan, "tail"):
        units[-1] = replace(
            final, scan=replace(final.scan, body=replaced[id(final.scan.body)])
        )
    return Grafted(
        request,
        replace(query, units=tuple(units)),
        unit,
        record,
        tuple(collects[at] for at in sorted(collects)),
        artifact,
    )


def _published_names(flat, columns) -> tuple[Any, ...]:
    """The flat CTE header without the names of withheld positions."""
    return tuple(
        symbol
        for symbol, column in zip(flat.cte_columns, columns, strict=True)
        if type(column) is not unnesting.WithheldPort
    )


def _emit_parameterized(directory, body: str):
    """One PostgreSQL emission of a stand-in that binds query parameters."""
    item = probe.join_witness("postgres", body)
    contract = json.loads(item["contract"])
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        }
    )
    _, outcome = probe.build_case(
        directory, item["source"], probe.encoded(contract).decode(), item["policy"]
    )
    assert outcome.artifact is not None, outcome
    return outcome.artifact


def build(directory, case: str) -> Grafted:
    body, position, reads = CASES[case]
    if case in PARAMETERIZED:
        artifact = _emit_parameterized(directory, body)
    else:
        _, artifact = collecting.emit(directory, body)
    return graft(artifact, position=position, reads=reads)


def other_join(directory, kind: str):
    """The real JOIN record of a flat stand-in of another kind."""
    _, artifact = collecting.emit(directory, OTHER.format(join=OTHER_JOINS[kind]))
    (unit,) = _join_bodies(artifact.ast)
    return unit.join
