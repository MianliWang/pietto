"""Phase71 S12 collection admission: one operation predicate, the pre-connection
route and child-leaf checks.

Every gate reads the compiled operation closure, never only the final output
shape, so a collection that is unnested again before the output is gated too.
The child-leaf domain is the S10 result-binding owner's fixed allowlist.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import NoReturn

from pietto._project.project_execution import ExecutionError
from pietto._project.project_result_binding import CHILD_KINDS
from pietto._project.project_result_contract import NestedShape, ScalarShape

__all__: tuple[str, ...] = ()

# S09-A's frozen compiled vocabulary (project_compiled_schema COLLECT_OPERATOR
# and the "unnest" record kind); S12-B imports them once S09 is integrated.
_COLLECT_OPERATOR = ("collect", "collect")
_UNNEST = "unnest"
_PARENT_ROWS = 64
_CHILD_ROWS = 16
_TEXT_BYTES = 256


def _resource() -> NoReturn:
    raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")


@dataclass(frozen=True, slots=True, eq=False)
class CollectionReply:
    """One owned scalar reply used only by S12's source-bound preflight."""

    connection: object = field(repr=False)
    sql: str
    arguments: tuple
    metadata: tuple
    rows: tuple = field(repr=False)
    status: int


@dataclass(frozen=True, slots=True, eq=False)
class CollectionDomain:
    """The exact one-collection source closure S12 can bound."""

    output: object = field(repr=False)
    parent_source: object = field(repr=False)
    child_source: object = field(repr=False)
    child_fields: tuple[object, ...] = field(repr=False)
    child_tags: tuple[str, ...]
    row_fields: tuple[object, ...] = field(repr=False)
    row_tags: tuple[str, ...]
    unnest: bool


@dataclass(frozen=True, slots=True, eq=False)
class CollectionPreflight:
    request: object = field(repr=False)
    output: object = field(repr=False)
    connection: object = field(repr=False)
    qualification: object = field(repr=False)
    profile: tuple = field(repr=False)
    parent_source: object = field(repr=False)
    child_source: object = field(repr=False)
    child_fields: tuple[object, ...] = field(repr=False)
    child_tags: tuple[str, ...]
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


def _domain(request) -> CollectionDomain | None:
    """Re-derive the sole S12 source domain from verified current objects.

    A physical table count only bounds a result when the selected relation
    closure has no operation that can multiply or manufacture rows.  This is
    deliberately narrower than the SQL emitter: joins, sets, values, global
    aggregates, windows and table functions wait for their own bounds.
    """
    from pietto._project.project_result_output import (
        GeneralOutput,
        NestedOutputColumn,
        OutputColumn,
    )
    from pietto._project.project_sql_emission_nested import CollectColumn
    from pietto._project.project_sql_emission_results import ResultGroupColumn
    from pietto._project.project_sql_emission_contract import PreparedEmission

    completed = request.artifact.request.verification.completed
    plan = request.artifact.request.plan
    collects = tuple(plan.collects)
    if not collects:
        return None
    if len(collects) != 1:
        _resource()
    (collect,) = collects
    output, sources = request.output, request.artifact.request.sources
    if type(output) is not GeneralOutput or output.artifact is not request.artifact:
        _resource()

    def source_of(field):
        matches = tuple(
            source for source in sources if any(item is field for item in source.fields)
        )
        if len(matches) != 1:
            _resource()
        return matches[0]

    def bound_for(port):
        matches = tuple(
            (source, item)
            for source in sources
            for item in source.fields
            if item.field is port.field
        )
        if len(matches) != 1:
            _resource()
        return matches[0]

    columns = output.columns
    if type(columns) is not tuple:
        _resource()
    unnest = False
    unnests = ()
    unnest_layout = ()
    parent = None
    children = ()
    if (
        len(columns) == 2
        and type(columns[0]) is OutputColumn
        and type(columns[1]) is NestedOutputColumn
    ):
        parent, collection = columns
        children = collection.children
        group = collection.original
        if type(group) is ResultGroupColumn:
            group = group.group
        if (
            type(group) is not CollectColumn
            or group.collect is not collect
            or getattr(collection.field.shape, "collect", None) is not collect
        ):
            _resource()
        parent_source = source_of(parent.source_field)
        child_fields = tuple(child.source_field for child in children)
        child_tags = tuple(child.realization.tag for child in children)
        row_fields, row_tags = child_fields, child_tags
    else:
        unnests = tuple(plan.unnests)
        if len(unnests) != 1:
            _resource()
        unnest_record = unnests[0]
        unnest_layout = getattr(unnest_record, "layout", ())
        if not all(type(item) is OutputColumn for item in columns):
            _resource()
        child_exports = tuple(getattr(unnest_record, "outputs", ()))
        child_ports = tuple(
            port for port in plan.all_exports if port.ref in collect.children
        )
        parent_ports = tuple(
            port for port in plan.all_exports if port.ref is collect.export
        )
        child_bindings = tuple(bound_for(port) for port in child_ports)
        parent_bindings = tuple(bound_for(port) for port in parent_ports)
        if (
            len(parent_bindings) != 1
            or len(child_ports) != len(collect.children)
            or tuple(port.ref for port in child_ports) != collect.children
            or len(child_bindings) != len(child_exports)
            or getattr(unnest_record, "collect", None) is not collect.ref
            or len(getattr(plan, "joins", ())) != 1
            or getattr(plan.joins[0], "ref", None)
            is not getattr(unnest_record, "join", None)
        ):
            _resource()
        ((parent_source, parent_field),) = parent_bindings
        child_source = child_bindings[0][0]
        child_fields = tuple(field for _source, field in child_bindings)
        child_tags = tuple(
            port.field.evidence.resolved_type.name for port in child_ports
        )
        row_fields = tuple(column.source_field for column in columns)
        row_tags = tuple(column.realization.tag for column in columns)
        if (
            parent_field.field.resolved_type.name != "Int"
            or not child_fields
            or any(tag not in CHILD_KINDS for tag in child_tags)
            or any(field is None for field in row_fields)
            or any(tag not in CHILD_KINDS for tag in row_tags)
            or any(source is not child_source for source, _field in child_bindings)
            or any(
                source_of(field) not in (parent_source, child_source)
                for field in row_fields
            )
        ):
            _resource()
        unnest = True
    if not unnest:
        if type(parent) is not OutputColumn:
            _resource()
        if (
            parent.realization.tag != "Int"
            or parent.source_field is None
            or type(children) is not tuple
            or not children
            or any(
                child.source_field is None or child.realization.tag not in CHILD_KINDS
                for child in children
            )
        ):
            _resource()
    if not unnest:
        if type(parent) is not OutputColumn:
            _resource()
        parent_field = parent.source_field
        if parent_field is None:
            _resource()
        parent_source = source_of(parent_field)
        child_fields = tuple(child.source_field for child in children)
        child_tags = tuple(child.realization.tag for child in children)
        row_fields, row_tags = child_fields, child_tags
        child_source = source_of(child_fields[0])
    child_sources = tuple(source_of(field) for field in child_fields)
    if any(source is not child_sources[0] for source in child_sources[1:]):
        _resource()
    child_source = child_sources[0]
    if (
        any(
            source is not parent_source and source is not child_source
            for source in sources
        )
        or not any(source is parent_source for source in sources)
        or not any(source is child_source for source in sources)
    ):
        _resource()
    if (
        any(
            getattr(plan, name, ())
            for name in (
                "joins",
                "set_bodies",
                "values_bodies",
                "aggregations",
                "windows",
            )
        )
        and not unnest
    ):
        _resource()
    if unnest and any(
        getattr(plan, name, ())
        for name in ("set_bodies", "values_bodies", "aggregations", "windows")
    ):
        _resource()
    root = getattr(completed, "root", None)
    records = getattr(root, "records", None)
    if root is None or not isinstance(records, Mapping):
        if root is not None or type(request.artifact.request) is not PreparedEmission:
            _resource()
    else:
        from pietto._project.project_compiled_schema import selected_relations

        entry = records.get(root.description.query)
        if entry is None:
            _resource()
        active = selected_relations(records, entry)
        join_layout = (
            unnest_layout[2]
            if unnest and type(unnest_layout) is tuple and len(unnest_layout) >= 3
            else None
        )
        permitted = frozenset({"source", "row", "result"}) | (
            frozenset({"join"}) if unnest else frozenset()
        )
        if (
            any(address.kind not in permitted for address in active)
            or any(
                address.kind == "join" and address != join_layout for address in active
            )
            or any(address.kind == "table_function" for address in active)
        ):
            _resource()
    return CollectionDomain(
        output,
        parent_source,
        child_source,
        child_fields,
        child_tags,
        row_fields,
        row_tags,
        unnest,
    )


def _queries(domain, limits):
    from pietto._project.project_execution_source import identifier

    def relation(source):
        return identifier(source.namespace) + "." + identifier(source.name)

    parent_cap = min(_PARENT_ROWS, limits.max_rows) + 1
    child_cap = _CHILD_ROWS + 1
    if domain.parent_source is domain.child_source:
        parent_cap = child_cap = min(parent_cap, child_cap)
    result = [
        ("SELECT current_setting('server_encoding')", (), 25),
        (
            "SELECT COUNT(*) FROM (SELECT 1 FROM "
            + relation(domain.parent_source)
            + ' LIMIT $1) AS "__pietto_nested_bound"',
            (parent_cap,),
            20,
        ),
        (
            "SELECT COUNT(*) FROM (SELECT 1 FROM "
            + relation(domain.child_source)
            + ' LIMIT $1) AS "__pietto_nested_bound"',
            (child_cap,),
            20,
        ),
    ]
    for source_field, tag in zip(domain.child_fields, domain.child_tags, strict=True):
        if tag == "Text":
            result.append(
                (
                    "SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("
                    + identifier(source_field.column)
                    + "),0),$1)),0) FROM "
                    + relation(domain.child_source),
                    (_TEXT_BYTES + 1,),
                    23,
                )
            )
    return tuple(result), parent_cap, child_cap


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


def _measure(domain, limits, parents, children, text_bytes):
    if (
        type(parents) is not int
        or type(children) is not int
        or any(
            type(value) is not int or not 0 <= value <= _TEXT_BYTES
            for value in text_bytes
        )
    ):
        _resource()

    def saturate(value, limit):
        return limit + 1 if value > limit else value

    if parents > min(_PARENT_ROWS, limits.max_rows) or children > _CHILD_ROWS:
        _resource()
    child_total = saturate(parents * children, 1 << 20)
    if child_total > 1 << 20:
        _resource()
    if domain.unnest:
        prepared = domain.output.artifact.request
        plan = prepared.plan
        if hasattr(plan, "joins"):
            (join,) = plan.joins
            kind = join.kind.value
        else:
            (unnest,) = plan.unnests
            kind = prepared.verification.completed.root.records[unnest.layout[2]].get(
                "kind"
            )
        per_parent = max(1, children) if kind == "left" else children
        rows = saturate(parents * per_parent, limits.max_rows)
        if rows > limits.max_rows:
            _resource()
    else:
        rows = parents

    def width(field, tag):
        if tag != "Text":
            return {"Int": 20, "Bool": 5}[tag]
        matches = tuple(
            index
            for index, (child, child_tag) in enumerate(
                zip(domain.child_fields, domain.child_tags, strict=True)
            )
            if child is field and child_tag == "Text"
        )
        if len(matches) != 1:
            _resource()
        text_index = sum(tag == "Text" for tag in domain.child_tags[: matches[0]])
        return text_bytes[text_index]

    def escaped(size):
        return saturate(max(4, 2 * size + 2), limits.batch_bytes)

    def array(size):
        if children == 0:
            return 4
        return saturate(
            4 + 2 + (children - 1) + children * escaped(size), limits.batch_bytes
        )

    if domain.unnest:
        row = 7
        for field, tag in zip(domain.row_fields, domain.row_tags, strict=True):
            row = saturate(row + 4 + escaped(width(field, tag)), limits.batch_bytes)
    else:
        row = 7 + 4 + escaped(20) + 4 + len(str(children))
        for field, tag in zip(domain.child_fields, domain.child_tags, strict=True):
            row = saturate(row + array(width(field, tag)), limits.batch_bytes)
    batch = saturate(min(rows, limits.batch_rows) * row, limits.batch_bytes)
    total = saturate(rows * row, limits.max_bytes)
    if (
        row > limits.batch_bytes
        or batch > limits.batch_bytes
        or total > limits.max_bytes
    ):
        _resource()
    return row, batch, total


def run_collection_preflight(
    request, read, *, connection, qualification, profile
) -> CollectionPreflight | None:
    """Read and bind S12's fixed limits in the already-qualified snapshot."""
    domain = _domain(request)
    if domain is None:
        return None
    if connection is None or qualification is None or type(profile) is not tuple:
        _resource()
    queries, parent_cap, child_cap = _queries(domain, request.limits)
    encoding_query, parent_query, child_query, *text_queries = queries
    replies = []
    reply = read(encoding_query[0], encoding_query[1])
    replies.append(reply)
    if _value(reply, connection, *encoding_query) != "UTF8":
        raise ExecutionError("POSTGRES_SOURCE_ENCODING")
    reply = read(parent_query[0], parent_query[1])
    replies.append(reply)
    parents = _value(reply, connection, *parent_query)
    if type(parents) is not int or not 0 <= parents < parent_cap:
        _resource()
    reply = read(child_query[0], child_query[1])
    replies.append(reply)
    children = _value(reply, connection, *child_query)
    if type(children) is not int or not 0 <= children < child_cap:
        _resource()
    text_bytes = []
    for query in text_queries:
        reply = read(query[0], query[1])
        replies.append(reply)
        text_bytes.append(_value(reply, connection, *query))
    text_bytes = tuple(text_bytes)
    row, batch, total = _measure(domain, request.limits, parents, children, text_bytes)
    return CollectionPreflight(
        request,
        domain.output,
        connection,
        qualification,
        profile,
        domain.parent_source,
        domain.child_source,
        domain.child_fields,
        domain.child_tags,
        parents,
        children,
        text_bytes,
        row,
        batch,
        total,
        tuple(replies),
    )


def verify_collection_preflight(
    request, receipt, *, connection, qualification, profile
) -> None:
    """Re-derive the domain, fixed reads and arithmetic before carrier SQL."""
    if receipt is None:
        return
    domain = _domain(request)
    if (
        type(receipt) is not CollectionPreflight
        or receipt.request is not request
        or domain is None
        or receipt.output is not domain.output
        or receipt.connection is not connection
        or receipt.qualification is not qualification
        or receipt.profile != profile
        or receipt.parent_source is not domain.parent_source
        or receipt.child_source is not domain.child_source
        or receipt.child_fields != domain.child_fields
        or receipt.child_tags != domain.child_tags
    ):
        _resource()
    queries, parent_cap, child_cap = _queries(domain, request.limits)
    if len(receipt.replies) != len(queries):
        _resource()
    values = tuple(
        _value(reply, connection, sql, arguments, oid)
        for reply, (sql, arguments, oid) in zip(receipt.replies, queries, strict=True)
    )
    if (
        values[0] != "UTF8"
        or values[1] != receipt.parents
        or values[2] != receipt.children
        or values[3:] != receipt.text_bytes
        or not 0 <= receipt.parents < parent_cap
        or not 0 <= receipt.children < child_cap
        or _measure(
            domain,
            request.limits,
            receipt.parents,
            receipt.children,
            receipt.text_bytes,
        )
        != (receipt.row_bytes, receipt.batch_bytes, receipt.total_bytes)
    ):
        _resource()
