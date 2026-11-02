"""Bound collection execution from the verified relation graph and output carriers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NoReturn

from pietto._project.project_execution import ExecutionError
from pietto._project.project_result_binding import CHILD_KINDS
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_result_contract import NestedShape, ScalarShape

__all__: tuple[str, ...] = ()
_COLLECT_OPERATOR = ("collect", "collect")
_UNNEST = "unnest"
_PARENT_ROWS = 64
_CHILD_ROWS = 16
_TEXT_BYTES = 256


def _resource() -> NoReturn:
    raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")


@dataclass(frozen=True, slots=True, eq=False)
class CollectionReply:
    connection: object = field(repr=False)
    sql: str
    arguments: tuple
    metadata: tuple
    rows: tuple = field(repr=False)
    status: int


@dataclass(frozen=True, slots=True, eq=False)
class CollectionGroup:
    """One canonical Collect producer, whether or not its carrier is retained."""

    collect: Any = field(repr=False)
    producer: Any = field(repr=False)
    columns: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CollectionDomain:
    output: Any = field(repr=False)
    groups: tuple[CollectionGroup, ...] = field(repr=False)
    parent_sources: tuple = field(repr=False)
    count_sources: tuple = field(repr=False)
    child_sources: tuple = field(repr=False)
    # Every final nested output occurrence has its own index, including aliases.
    retained: tuple[int, ...]
    expansions: tuple = field(repr=False)
    text_fields: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CollectionPreflight:
    request: Any = field(repr=False)
    output: Any = field(repr=False)
    connection: object = field(repr=False)
    qualification: object = field(repr=False)
    profile: tuple = field(repr=False)
    domain: CollectionDomain = field(repr=False)
    source_counts: tuple[int, ...]
    child_counts: tuple[int, ...]
    parents: int
    children: int
    text_bytes: tuple[int, ...]
    row_bytes: int
    batch_bytes: int
    total_bytes: int
    replies: tuple[CollectionReply, ...] = field(repr=False)


def collection_operations(records) -> frozenset[str]:
    """The collection operations of one compiled root's complete records."""
    found = set()
    for address, record in records.items():
        if address.kind == _UNNEST:
            found.add("unnest")
        elif (
            address.kind == "operation" and record.get("operator") == _COLLECT_OPERATOR
        ):
            found.add("collect")
    return frozenset(found)


def request_collection_operations(request) -> frozenset[str]:
    """Discover collection operations without assuming a compiled root exists."""
    prepared = request.artifact.request
    plan = getattr(prepared, "plan", None)
    if plan is not None:
        found = set()
        if getattr(plan, "collects", ()):
            found.add("collect")
        if getattr(plan, "unnests", ()):
            found.add("unnest")
        if found:
            return frozenset(found)
    root = getattr(getattr(prepared, "verification", None), "completed", None)
    records = getattr(getattr(root, "root", None), "records", None)
    return (
        collection_operations(records) if isinstance(records, Mapping) else frozenset()
    )


def admit_collection_route(request) -> None:
    """A collection runs only on an unguarded, unrefined postgres_rows request;
    checked before the route's premise, driver or connection."""
    if not request_collection_operations(request):
        return
    prepared = request.artifact.request
    root = getattr(getattr(prepared, "verification", None), "completed", None)
    records = getattr(getattr(root, "root", None), "records", None)
    if isinstance(records, Mapping):
        from pietto._project.project_compiled_schema import Address

        policy = records.get(Address("policy", 0))
        if policy is None:
            _resource()
        guarded = policy.get("guarded")
        refinement = policy.get("refinement")
    else:
        from pietto._project.project_execution import ExecutionRequest
        from pietto._project.project_sql_emission_contract import PreparedEmission

        if (
            type(request) is not ExecutionRequest
            or type(prepared) is not PreparedEmission
        ):
            _resource()
        guarded = False
        refinement = None
    if request.route != "postgres_rows" or guarded or refinement is not None:
        raise ExecutionError("COLLECTION_ROUTE")


def admit_nested_shape(contract) -> None:
    """Every child of a nested field is in S12's admitted leaf domain."""
    nested = [
        leaf.shape for leaf in contract.shape.fields if type(leaf.shape) is NestedShape
    ]
    if not nested:
        return
    if any(
        type(child.shape) is not ScalarShape
        or child.shape.canonical.name not in CHILD_KINDS
        for shape in nested
        for child in shape.fields
    ):
        raise ExecutionError("COLLECTION_LEAF")


def _inputs(unit):
    from pietto._project.project_sql_emission_ast import (
        RowBody,
        RowJoinUse,
        RowNamedUse,
        RowScan,
        RowStageUse,
    )
    from pietto._project.project_sql_emission_contract import BoundSource
    from pietto._project.project_sql_emission_joins import JoinBody
    from pietto._project.project_sql_emission_results import RowResultBody, RowResultUse
    from pietto._project.project_sql_emission_unnest import UnnestRows

    if type(unit) in (BoundSource, UnnestRows):
        return ()
    if type(unit) is JoinBody:
        return tuple(item.producer for item in unit.inputs)
    if type(unit) in (RowBody, RowResultBody):
        if type(unit.scan) is RowScan:
            return (unit.scan.realization,)
        if type(unit.scan) in (RowJoinUse, RowNamedUse, RowStageUse, RowResultUse):
            return (unit.scan.body,)
    _resource()


def _source_occurrences(unit):
    from pietto._project.project_sql_emission_contract import BoundSource

    active = set()

    def visit(current):
        if id(current) in active:
            _resource()
        if type(current) is BoundSource:
            return (current,)
        active.add(id(current))
        try:
            return tuple(
                source for child in _inputs(current) for source in visit(child)
            )
        finally:
            active.remove(id(current))

    return visit(unit)


def _domain(request) -> CollectionDomain | None:
    from pietto._project.project_result_output import (
        GeneralOutput,
        NestedOutputColumn,
        OutputColumn,
    )
    from pietto._project.project_sql_emission_nested import CollectColumn
    from pietto._project.project_sql_emission_joins import JoinBody
    from pietto._project.project_sql_emission_unnest import UnnestRows

    plan = request.artifact.request.plan
    collects = tuple(plan.collects)
    if not collects:
        return None
    output = request.output
    if type(output) is not GeneralOutput or output.artifact is not request.artifact:
        _resource()
    found, expansions, active, visited = {}, [], set(), set()

    def visit(unit):
        if id(unit) in active:
            _resource()
        if id(unit) in visited:
            return
        active.add(id(unit))
        for child in _inputs(unit):
            visit(child)
        if type(unit) is JoinBody and type(unit.inputs[1].producer) is UnnestRows:
            expansions.append(unit)
        for column in getattr(unit, "columns", ()):
            if type(column) is CollectColumn:
                previous = found.setdefault(column.collect.ref, column)
                if previous is not column:
                    _resource()
                visit(column.lateral.target.producer)
        active.remove(id(unit))
        visited.add(id(unit))

    visit(output.units[-1])
    if len(found) != len(collects) or any(c.ref not in found for c in collects):
        _resource()
    groups = tuple(
        CollectionGroup(
            c,
            found[c.ref].lateral.target.producer,
            tuple(item.column for item in found[c.ref].lateral.target.producer.columns),
        )
        for c in collects
    )
    if any(not group.columns for group in groups):
        _resource()
    parents = _source_occurrences(output.units[-1])
    children = tuple(
        source for group in groups for source in _source_occurrences(group.producer)
    )
    sources = tuple(dict.fromkeys((*parents, *children)))
    if not parents or any(
        source not in request.artifact.request.sources for source in sources
    ):
        _resource()
    retained = []
    scalar_columns = []
    for column in output.columns:
        if type(column) is NestedOutputColumn:
            matches = tuple(
                i
                for i, group in enumerate(groups)
                if group.collect is column.field.shape.collect
            )
            if len(matches) != 1:
                _resource()
            retained.append(matches[0])
        elif type(column) is OutputColumn:
            scalar_columns.append(column.original.column)
        else:
            _resource()
    # Count query acquisition may be shared; every scalar/carrier occurrence is
    # still charged independently by _measure.
    text_fields = []
    for column in (*scalar_columns, *(c for group in groups for c in group.columns)):
        realization = column.realization
        if realization is None or realization.tag not in CHILD_KINDS:
            _resource()
        if realization.tag == "Text":
            if column.field is None:
                maximum = realization.domain.get("max_characters")
                if type(maximum) is not int or not 0 <= maximum <= _TEXT_BYTES // 4:
                    _resource()
            elif all(column.field is not old for old in text_fields):
                matches = tuple(
                    source
                    for source in sources
                    if any(column.field is f for f in source.fields)
                )
                if len(matches) != 1:
                    _resource()
                text_fields.append(column.field)
    for join in expansions:
        if (
            sum(
                group.collect.ref is join.inputs[1].producer.unnest.collect
                for group in groups
            )
            != 1
        ):
            _resource()
    return CollectionDomain(
        output,
        groups,
        parents,
        sources,
        children,
        tuple(retained),
        tuple(expansions),
        tuple(text_fields),
    )


def _queries(domain, limits):
    from pietto._project.project_execution_source import identifier

    def relation(source):
        return identifier(source.namespace) + "." + identifier(source.name)

    caps = tuple(
        min(
            _CHILD_ROWS if source in domain.child_sources else _PARENT_ROWS,
            min(_PARENT_ROWS, limits.max_rows)
            if source in domain.parent_sources
            else _CHILD_ROWS,
        )
        + 1
        for source in domain.count_sources
    )
    queries: list[tuple[str, tuple[int, ...], int]] = [
        ("SELECT current_setting('server_encoding')", (), 25)
    ]
    for source, cap in zip(domain.count_sources, caps, strict=True):
        queries.append(
            (
                "SELECT COUNT(*) FROM (SELECT 1 FROM "
                + relation(source)
                + ' LIMIT $1) AS "__pietto_nested_bound"',
                (cap,),
                20,
            )
        )
    for source_field in domain.text_fields:
        matches = tuple(
            s for s in domain.count_sources if any(source_field is f for f in s.fields)
        )
        if len(matches) != 1:
            _resource()
        queries.append(
            (
                "SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("
                + identifier(source_field.column)
                + "),0),$1)),0) FROM "
                + relation(matches[0]),
                (_TEXT_BYTES + 1,),
                23,
            )
        )
    return tuple(queries), caps


def _value(reply, connection, sql, arguments, oid):
    if (
        type(reply) is not CollectionReply
        or reply.connection is not connection
        or reply.sql != sql
        or reply.arguments != arguments
        or reply.status != 2
        or type(reply.metadata) is not tuple
        or len(reply.metadata) != 1
        or type(reply.metadata[0]) is not tuple
        or len(reply.metadata[0]) != 3
        or reply.metadata[0][0] != 0
        or type(reply.metadata[0][1]) is not str
        or reply.metadata[0][2] != oid
        or type(reply.rows) is not tuple
        or len(reply.rows) != 1
        or type(reply.rows[0]) is not tuple
        or len(reply.rows[0]) != 1
    ):
        _resource()
    return reply.rows[0][0]


def _sat_add(left, right, limit):
    return limit + 1 if left > limit or right > limit - left else left + right


def _sat_mul(left, right, limit):
    if left == 0 or right == 0:
        return 0
    return limit + 1 if left > limit // right else left * right


def _row_upper_bound(unit, counts, group_bounds, limit):
    """Memoize node bounds while retaining every JOIN input edge."""
    from pietto._project.project_sql_emission_contract import BoundSource
    from pietto._project.project_sql_emission_joins import JoinBody
    from pietto._project.project_sql_emission_unnest import UnnestRows

    cache, active = {}, set()

    def visit(item):
        if id(item) in cache:
            return cache[id(item)]
        if id(item) in active:
            _resource()
        active.add(id(item))
        if type(item) is BoundSource:
            if item not in counts:
                _resource()
            value = counts[item]
        elif type(item) is UnnestRows:
            if item.unnest.collect not in group_bounds:
                _resource()
            value = group_bounds[item.unnest.collect]
        elif type(item) is JoinBody:
            left, right = (visit(child) for child in _inputs(item))
            kind = item.join.kind.value
            if kind in {"cross", "inner"}:
                value = _sat_mul(left, right, limit)
            elif kind == "left":
                value = _sat_mul(left, max(1, right), limit)
            elif kind == "right":
                value = _sat_mul(max(1, left), right, limit)
            elif kind == "full":
                value = _sat_add(
                    _sat_add(_sat_mul(left, right, limit), left, limit), right, limit
                )
            elif kind in {"semi", "anti"}:
                value = left
            else:
                _resource()
        else:
            parents = _inputs(item)
            if len(parents) != 1:
                _resource()
            value = visit(parents[0])
            aggregation = getattr(item, "aggregation", None)
            if aggregation is not None:
                if aggregation.mode == "global":
                    value = 1
                elif aggregation.mode != "grouped":
                    _resource()
            limited = getattr(item, "limit", None)
            if limited is not None:
                if type(limited.value) is not int or limited.value < 0:
                    _resource()
                value = min(value, limited.value)
        if type(value) is not int or value < 0:
            _resource()
        value = min(value, limit + 1)
        active.remove(id(item))
        cache[id(item)] = value
        return value

    return visit(unit)


def _bounds(domain, limits, values):
    _, caps = _queries(domain, limits)
    if len(values) != len(caps) or any(
        type(n) is not int or not 0 <= n < cap
        for n, cap in zip(values, caps, strict=True)
    ):
        _resource()
    counts = dict(zip(domain.count_sources, values, strict=True))
    children = tuple(
        _row_upper_bound(group.producer, counts, {}, _CHILD_ROWS)
        for group in domain.groups
    )
    if any(n > _CHILD_ROWS for n in children):
        _resource()
    return counts, children


def _measure(domain, limits, source_counts, children, text_bytes):
    from pietto._project.project_result_output import NestedOutputColumn

    counts, actual_children = _bounds(domain, limits, source_counts)
    if (
        children != actual_children
        or len(text_bytes) != len(domain.text_fields)
        or any(type(n) is not int or not 0 <= n <= _TEXT_BYTES for n in text_bytes)
    ):
        _resource()
    group_bounds = {
        g.collect.ref: n for g, n in zip(domain.groups, children, strict=True)
    }
    rows = _row_upper_bound(
        domain.output.units[-1], counts, group_bounds, limits.max_rows
    )
    child_total = 0
    for index in domain.retained:
        child_total = _sat_add(
            child_total, _sat_mul(rows, children[index], 1 << 20), 1 << 20
        )
    for join in domain.expansions:
        left = _row_upper_bound(
            join.inputs[0].producer, counts, group_bounds, limits.max_rows
        )
        child_total = _sat_add(
            child_total,
            _sat_mul(
                left, group_bounds[join.inputs[1].producer.unnest.collect], 1 << 20
            ),
            1 << 20,
        )
    if rows > limits.max_rows or child_total > 1 << 20:
        _resource()

    def width(column):
        realized = column.realization
        tag = realized.tag
        if tag == "Text":
            if column.field is None:
                return 4 * realized.domain["max_characters"]
            matches = tuple(
                i for i, f in enumerate(domain.text_fields) if f is column.field
            )
            if len(matches) != 1:
                _resource()
            return text_bytes[matches[0]]
        if tag == "Decimal":
            precision, scale = (realized.domain.get(k) for k in ("precision", "scale"))
            if (
                type(precision) is not int
                or type(scale) is not int
                or not 1 <= precision <= 65
                or not 0 <= scale <= min(precision, 30)
            ):
                _resource()
            return precision + 1 + (scale > 0)
        return {
            "Int": 20,
            "Bool": 5,
            "Float": 24,
            "Date": 12,
            "Timestamp": 28,
            "UUID": 38,
        }[tag]

    def escaped(size):
        return max(
            4, _sat_add(_sat_mul(2, size, limits.batch_bytes), 2, limits.batch_bytes)
        )

    def array(size, count):
        return (
            4
            if count == 0
            else _sat_add(
                5 + count,
                _sat_mul(count, escaped(size), limits.batch_bytes),
                limits.batch_bytes,
            )
        )

    row, nested_index = 7, 0
    for column in domain.output.columns:
        if type(column) is NestedOutputColumn:
            index = domain.retained[nested_index]
            nested_index += 1
            count, group = children[index], domain.groups[index]
            present = (
                4
                + len(str(count))
                + sum(array(width(child), count) for child in group.columns)
            )
            # An unmatched outer JOIN nulls the count and every array carrier.
            absent = 8 + 4 * len(group.columns)
            row = _sat_add(
                row,
                (
                    max(present, absent)
                    if column.field.nullability
                    is not ProjectRowFieldNullability.NON_NULL
                    else present
                ),
                limits.batch_bytes,
            )
        else:
            row = _sat_add(
                row,
                _sat_add(4, escaped(width(column.original.column)), limits.batch_bytes),
                limits.batch_bytes,
            )
    batch = _sat_mul(min(rows, limits.batch_rows), row, limits.batch_bytes)
    total = _sat_mul(rows, row, limits.max_bytes)
    if (
        row > limits.batch_bytes
        or batch > limits.batch_bytes
        or total > limits.max_bytes
    ):
        _resource()
    return row, batch, total


def _same_domain(actual, expected):
    return (
        type(actual) is CollectionDomain
        and actual.output is expected.output
        and actual.parent_sources == expected.parent_sources
        and actual.count_sources == expected.count_sources
        and actual.child_sources == expected.child_sources
        and actual.retained == expected.retained
        and actual.expansions == expected.expansions
        and actual.text_fields == expected.text_fields
        and len(actual.groups) == len(expected.groups)
        and all(
            a.collect is b.collect
            and a.producer is b.producer
            and a.columns == b.columns
            for a, b in zip(actual.groups, expected.groups, strict=True)
        )
    )


def run_collection_preflight(request, read, *, connection, qualification, profile):
    domain = _domain(request)
    if domain is None:
        return None
    if connection is None or qualification is None or type(profile) is not tuple:
        _resource()
    queries, caps = _queries(domain, request.limits)
    replies, values = [], []
    for index, query in enumerate(queries):
        reply = read(query[0], query[1])
        value = _value(reply, connection, *query)
        if index == 0:
            if value != "UTF8":
                raise ExecutionError("POSTGRES_SOURCE_ENCODING")
        elif index <= len(caps):
            if type(value) is not int or not 0 <= value < caps[index - 1]:
                _resource()
        elif type(value) is not int or not 0 <= value <= _TEXT_BYTES:
            _resource()
        replies.append(reply)
        values.append(value)
    source_counts = tuple(values[1 : 1 + len(caps)])
    text_bytes = tuple(values[1 + len(caps) :])
    counts, children = _bounds(domain, request.limits, source_counts)
    row, batch, total = _measure(
        domain, request.limits, source_counts, children, text_bytes
    )
    return CollectionPreflight(
        request,
        domain.output,
        connection,
        qualification,
        profile,
        domain,
        source_counts,
        children,
        counts[domain.parent_sources[0]],
        children[0],
        text_bytes,
        row,
        batch,
        total,
        tuple(replies),
    )


def verify_collection_preflight(
    request, receipt, *, connection, qualification, profile
):
    if receipt is None:
        return
    domain = _domain(request)
    if (
        type(receipt) is not CollectionPreflight
        or domain is None
        or receipt.request is not request
        or receipt.output is not domain.output
        or receipt.connection is not connection
        or receipt.qualification is not qualification
        or receipt.profile != profile
        or not _same_domain(receipt.domain, domain)
    ):
        _resource()
    queries, caps = _queries(domain, request.limits)
    if type(receipt.replies) is not tuple or len(receipt.replies) != len(queries):
        _resource()
    values = tuple(
        _value(reply, connection, *query)
        for reply, query in zip(receipt.replies, queries, strict=True)
    )
    source_counts = values[1 : 1 + len(caps)]
    text_bytes = values[1 + len(caps) :]
    counts, children = _bounds(domain, request.limits, source_counts)
    if (
        values[0] != "UTF8"
        or receipt.source_counts != source_counts
        or receipt.child_counts != children
        or receipt.text_bytes != text_bytes
        or receipt.parents != counts[domain.parent_sources[0]]
        or receipt.children != children[0]
        or _measure(domain, request.limits, source_counts, children, text_bytes)
        != (receipt.row_bytes, receipt.batch_bytes, receipt.total_bytes)
    ):
        _resource()
