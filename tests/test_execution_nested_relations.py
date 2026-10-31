"""Phase71 S09: the compiled form of a Collect read and the reserved Unnest.

The first part changes real compiled builds of flat programs record by record
and pins them again: a changed description that verifies proves its structure
only. The second part builds every admitted PostgreSQL Collect shape for real,
loads its bundle without its project and lowers it to the live statement's
bytes, contract and digest.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import sys

import pytest

import _pietto_execution_nested_oracle as oracle
import _pietto_sql_emission as emission
import _pietto_sql_nested_collect as collecting
from _pietto_plan_nested import HEAD, SHAPES, project
import pietto.execution as execution
from pietto._project import project_sql_emission_nested as nested
from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_compiled_lowering import emit_compiled
from pietto._project.project_compiled_schema import (
    BLOCK_READ_OPERATORS,
    COLLECT_OPERATOR,
    FIELDS,
    Address,
    CompiledError,
    Record,
    content_pin,
    decode,
    encode,
    selected_relations,
)
from pietto._project.project_compiled_verification import (
    RELATIONS,
    verify_description,
)
from pietto._project.project_result_contract import (
    NestedShape,
    ResultError,
    build_result_contract,
)
from pietto._project.project_result_ipc import contract_digest
from pietto._project.project_sql_emission_cli import POLICIES, emit_project
from pietto._project.project_sql_plan_verification import verify_compiled_sql_plan

pytestmark = pytest.mark.ci_workload("general-runtime")

ORDERED = "        order by:\n            id desc\n        limit 2\n"  # hidden key
CLOSED = "    let n:\n        from rhs\n        select:\n            key\n" + ORDERED
# A captured ordered let compiles inline at the one read that renders it.
CAPTURED = (
    "    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            key\n"
    "        order by:\n            id\n        limit 1\n"
)
PROGRAMS = {
    "postgres": "query result:\n"
    + CAPTURED
    + CLOSED
    + "    from lhs\n    where lhs.id > 0\n"
    + "    select:\n        a = lhs.id\n        k = scalar n.key\n"
    + "        c = scalar m.key\n    limit 5\n",
    "join": "query result:\n"
    + CLOSED
    + "    from lhs\n    inner join rhs on lhs.id == rhs.id and rhs.key > 0\n"
    + "    select:\n        a = lhs.id\n        k = scalar n.key\n",
    "mysql": "query result:\n"
    + CLOSED
    + "    from lhs\n    select:\n        a = lhs.id\n        k = scalar n.key\n",
    # The let's parent is no entry: the entry reads it with `from`.
    "parent": "query mid:\n"
    + CLOSED
    + "    from lhs\n    select:\n        a = lhs.id\n        k = scalar n.key\n"
    + "query result:\n    from mid\n    select:\n        a\n",
    # A table function's declaration shares the place of the query reading it.
    "series": "query result:\n"
    + CLOSED
    + CLOSED.replace("let n:", "let m:").replace("from rhs", "from lhs")
    + "    from generate_series(1, 3, 1) as g\n    where g > 0\n"
    + "    select:\n        a = g\n        k = scalar n.key\n"
    + "        j = scalar m.key\n",
}
COLLECTION = ("collection", "non_null")
DRIVERS = ("psycopg", "psycopg_binary", "psycopg_c", "pyarrow")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    result = {}
    for name, body in PROGRAMS.items():
        item = emission.join_witness("mysql" if name == "mysql" else "postgres", body)
        checked, outcome = emission.build_case(
            tmp_path_factory.mktemp(name),
            item["source"],
            item["contract"],
            item["policy"],
        )
        assert checked.verified and outcome.status == "VERIFIED", outcome
        result[name] = build_compiled(outcome.artifact)
    return result


def _records(description):
    return {r.address: r for r in description.records}


def _set(record, **fields):
    names = FIELDS[record.address.kind]
    values = list(record.values)
    for name, value in fields.items():
        values[names.index(name)] = value
    return Record(record.address, tuple(values))


def _changed(description, *records):
    new = {r.address: r for r in records}
    return dataclasses.replace(
        description,
        members=tuple(
            (name, tuple(new.get(r.address, r) for r in group))
            for name, group in description.members
        ),
    )


def _one(records, kind, **fields):
    (found,) = (
        r
        for r in records.values()
        if r.address.kind == kind and all(r.get(n) == v for n, v in fields.items())
    )
    return found


def _collected(description):
    """Each scalar read of a let's parent projection row read as a Collect,
    with the ports and any output that carry its value."""
    records = _records(description)
    changed = []
    for block in (
        r for r in records.values() if r.address.kind == "expression_block_use"
    ):
        operation = records[block.get("operation")]
        assert operation.get("operator") == ("scalar", "scalar")
        port = _one(records, "port", source=operation.address)
        # A result unit over the row carries the value through its read.
        carried = {port.address} | {
            _one(records, "port", source=r.address).address
            for r in records.values()
            if r.address.kind == "read" and r.get("port") == port.address
        }
        changed += [
            _set(block, column=None),
            _set(operation, operator=COLLECT_OPERATOR, logical=COLLECTION),
            *(_set(records[a], logical=COLLECTION) for a in carried),
            *(
                _set(o, logical=COLLECTION)
                for o in records.values()
                if o.address.kind == "output" and o.get("port") in carried
            ),
        ]
    return _changed(description, *changed)


def _refused(description):
    with pytest.raises(CompiledError) as caught:
        verify_description(description)
    return str(caught.value)


def _load(build, raw):
    """``raw`` loaded under its own pin and the build's other records."""
    return load_compiled(
        raw,
        expected_pin=content_pin(raw),
        accepted_producer=build.producer,
        accepted_compatibility=build.compatibility,
    )


def _unnest(records, position):
    owner = _one(records, "declaration", label="result")
    source = _one(records, "port", owner=Address("source", 0), ordinal=0)
    return Record(
        Address("unnest", position),
        (owner.address, 0, source.address, (), (), (None, (), "u0", False, None)),
    )


def _with(description, member, records, *, first):
    return dataclasses.replace(
        description,
        members=tuple(
            (name, (*records, *group) if first else (*group, *records))
            if name == member
            else (name, group)
            for name, group in description.members
        ),
    )


def test_collect_is_no_scalar_block_read():
    assert COLLECT_OPERATOR == ("collect", "collect")
    assert COLLECT_OPERATOR not in BLOCK_READ_OPERATORS


@pytest.mark.parametrize(
    "place", (("structure", True), ("structure", False), ("outputs", False))
)
@pytest.mark.parametrize("count", (1, 2))
def test_a_reserved_unnest_record_decodes_and_is_refused(built, place, count):
    build = built["postgres"]
    description = build.root.description
    records = _records(description)
    assert FIELDS["unnest"] == (
        "owner",
        "position",
        "source",
        "fields",
        "outputs",
        "layout",
    )
    assert "unnest" not in RELATIONS
    member, first = place
    forged = _with(
        description,
        member,
        tuple(_unnest(records, i) for i in range(count)),
        first=first,
    )
    raw = encode(forged)
    assert decode(raw) == forged
    reserved = _records(forged)
    assert not any(
        a.kind == "unnest" for a in selected_relations(reserved, reserved[forged.query])
    )
    assert _refused(forged) == "COMPILED_UNNEST_UNAVAILABLE"
    with pytest.raises(CompiledError, match="^COMPILED_UNNEST_UNAVAILABLE$"):
        _load(build, raw)
    before = set(sys.modules)
    with pytest.raises(execution.RequestRejected) as caught:
        execution.load_bundle(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=build.producer,
            accepted_compatibility=build.compatibility[4],
        )
    assert (caught.value.code, caught.value.detail) == (
        "PIE-R1008",
        "COMPILED_UNNEST_UNAVAILABLE",
    )
    assert caught.value.attempt is None and caught.value.outcome is None
    assert not {m for m in set(sys.modules) - before if m.split(".")[0] in DRIVERS}


def test_an_unnest_record_of_another_width_is_no_record(built):
    build = built["postgres"]
    records = _records(build.root.description)
    record = _unnest(records, 0)
    narrow = Record(record.address, record.values[:5])
    raw = encode(_with(build.root.description, "structure", (narrow,), first=False))
    with pytest.raises(CompiledError, match="^COMPILED_FIELDS$"):
        decode(raw)


def test_the_described_collects_verify_as_structure(built):
    for name in ("postgres", "join", "parent"):
        description = _collected(built[name].root.description)
        verify_description(description)
        records = _records(description)
        collects = [
            r
            for r in records.values()
            if r.address.kind == "operation" and r.get("operator") == COLLECT_OPERATOR
        ]
        assert len(collects) == (2 if name == "postgres" else 1)
        # The hidden ORDER key of each collected let stays a helper port of
        # its projection row: the ordering reads a port the result drops.
        for block in (
            r for r in records.values() if r.address.kind == "expression_block_use"
        ):
            result = records[block.get("producer")]
            (key, _), *_ = result.get("ordering")
            hidden = records[key].get("port")
            assert hidden not in {
                records[p].get("port") for p in result.get("projection")
            }


def _postgres(built):
    description = _collected(built["postgres"].root.description)
    records = _records(description)
    closed, captured = sorted(
        (r for r in records.values() if r.address.kind == "expression_block_use"),
        key=lambda r: r.address.position,
    )
    assert records[closed.get("producer")].get("layout")[-1] is not None
    assert records[captured.get("producer")].get("layout")[-1] is None
    where = _one(
        records,
        "row",
        stage="where",
        owner=records[closed.get("consumer")].get("owner"),
    )
    return description, records, closed, captured, where


def test_a_collect_reads_one_ordered_let_result_into_the_entry_projection(built):
    description, records, closed, captured, where = _postgres(built)
    collect = records[closed.get("operation")]
    producer = records[closed.get("producer")]
    projection = records[producer.get("input")]
    cases = {
        "column": _set(closed, column=0),
        "producer_projection": _set(closed, producer=projection.address),
        "unordered_producer": _set(producer, ordering=()),
        "consumer_of_a_let": _set(closed, consumer=projection.address),
        # Two Collects of one captured let: its inline unit renders once.
        "inline_read_twice": _set(closed, producer=captured.get("producer")),
    }
    for name, changed in cases.items():
        category = _refused(_changed(description, changed))
        assert category == "COMPILED_EXPRESSION_BLOCK_USE", name
    # One Collect has exactly one block use and no operand.
    assert (
        _refused(_changed(description, _set(captured, operation=collect.address)))
        == "COMPILED_EXPRESSION_BLOCK_USE_INVENTORY"
    )
    operand = where.get("values")[0]
    assert (
        _refused(_changed(description, _set(collect, operands=(operand,))))
        == "COMPILED_OPERATOR_ARITY"
    )
    # Nowhere else than one direct value of its parent's projection row.
    comparison = records[where.get("predicate")]
    _, right = comparison.get("operands")
    for changed in (
        _set(where, predicate=collect.address),
        _set(comparison, operands=(collect.address, right)),
    ):
        category = _refused(_changed(description, changed))
        assert category == "COMPILED_COLLECT_PLACEMENT", changed
    joined = _collected(built["join"].root.description)
    join_records = _records(joined)
    block = _one(join_records, "expression_block_use")
    join = _one(join_records, "join")
    value = join_records[Address("join_value", 0)]
    assert (
        _refused(_changed(joined, _set(join, predicate=block.get("operation"))))
        == "COMPILED_COLLECT_PLACEMENT"
    )
    # A JOIN, aggregate or window value admits no operation at all.
    assert (
        _refused(_changed(joined, _set(value, input=block.get("operation"))))
        == "COMPILED_REFERENCE"
    )


def test_a_collect_stands_in_its_lets_parent_entry_or_not(built):
    description = _collected(built["parent"].root.description)
    records = _records(description)
    entry = records[records[description.query].get("declaration")]
    block = _one(records, "expression_block_use")
    parent = records[records[block.get("consumer")].get("owner")]
    port = _one(records, "port", source=block.get("operation"))
    # The entry's `from` input names the parent's collection port and reads
    # only the scalar column beside it.
    reader = _one(records, "use", producer=port.get("owner"))
    assert parent.address != entry.address
    assert records[reader.get("consumer")].get("owner") == entry.address
    assert port.address in reader.get("ports")
    verify_description(description)
    # A let of another table or query: the Collect stands outside its parent.
    let = records[records[block.get("producer")].get("owner")]
    moved = _set(
        let, **{n: entry.get(n) for n in ("module", "module_position", "position")}
    )
    assert _refused(_changed(description, moved)) == "COMPILED_EXPRESSION_BLOCK_USE"
    # The reader selects the collection again (S04 PIE-S2805).
    (scalar,) = (
        r
        for r in records.values()
        if r.address.kind == "read" and r.get("use") == reader.address
    )
    selected = _one(records, "port", source=scalar.address)
    again = (
        _set(scalar, port=port.address),
        _set(selected, logical=COLLECTION),
        _set(_one(records, "output", port=selected.address), logical=COLLECTION),
    )
    assert _refused(_changed(description, *again)) == "COMPILED_COLLECTION_PORT"


def test_a_table_function_beside_the_lets_is_no_parent(built):
    description = _collected(built["series"].root.description)
    verify_description(description)
    records = _records(description)
    (row,) = {
        r.get("consumer")
        for r in records.values()
        if r.address.kind == "expression_block_use"
    }
    function = _one(records, "table_function").get("owner")
    moved = _set(records[row], owner=function)
    assert _refused(_changed(description, moved)) == "COMPILED_EXPRESSION_BLOCK_USE"


def test_only_a_collect_and_its_carriers_have_a_collection_logical(built):
    description, records, closed, _, where = _postgres(built)
    collect = records[closed.get("operation")]
    port = _one(records, "port", source=collect.address)
    read = _one(records, "read", port=port.address)
    carried = _one(records, "port", source=read.address)
    output = _one(records, "output", port=carried.address)
    scanned = _one(records, "port", owner=Address("source", 0), ordinal=0)
    selected = _one(records, "port", source=records[port.get("owner")].get("values")[0])
    cases = {
        "COMPILED_COLLECT_LOGICAL": (
            _set(collect, logical=("collection", "nullable")),
            _set(collect, logical=("Int", "nullable")),
            _set(records[where.get("predicate")], logical=COLLECTION),
        ),
        "COMPILED_FIELD_LOGICAL": (
            _set(records[scanned.get("source")], logical=COLLECTION),
        ),
        "COMPILED_COLLECTION_PORT": (
            _set(scanned, logical=COLLECTION),
            _set(selected, logical=COLLECTION),
            _set(port, logical=("collection", "nullable")),
            _set(port, logical=("Int", "nullable")),
        ),
        # A collection is never an ORDER key of its parent nor part of its
        # parent's DISTINCT: a collected relation has no equality (S04 PIE-S2805).
        "COMPILED_COLLECTION_READ": (
            _set(records[carried.get("owner")], ordering=((read.address, "asc"),)),
            _set(records[carried.get("owner")], distinct=True),
        ),
        "COMPILED_OUTPUT_PORT": (
            _set(output, logical=("Int", "nullable")),
            _set(output, meaning="UUID"),
        ),
        # An operation names no site, a Collect or a flat value alike.
        "COMPILED_OPERATION_SITE": (
            _set(collect, site=_one(records, "site", role="where").address),
            _set(
                records[where.get("predicate")],
                site=_one(records, "site", role="where").address,
            ),
        ),
    }
    for category, changes in cases.items():
        for changed in changes:
            assert _refused(_changed(description, changed)) == category, changed
    # No JOIN value has one, whether or not a Collect stands beside it.
    flat = built["join"].root.description
    for joined in (flat, _collected(flat)):
        value = _records(joined)[Address("join_value", 0)]
        assert (
            _refused(_changed(joined, _set(value, logical=COLLECTION)))
            == "COMPILED_COLLECTION_LOGICAL"
        )


def test_a_mysql_description_has_no_collect(built):
    description = _collected(built["mysql"].root.description)
    assert _refused(description) == "COMPILED_COLLECT_TARGET"


# -- S09-B: real Collect artifacts, built, loaded and lowered ----------------

# Every admitted PostgreSQL shape of S08 and the sources it reads: a compiled
# build exports exactly the contract's sources.
REAL = {
    "closed": ("rows",),
    "top_k": ("rows", "orders"),
    "joined_capture": ("rows", "orders"),
    "joined_parent": ("rows",),
    "parallel": ("rows", "orders"),
    "ordered_parent": ("rows",),
    "windowed": ("rows",),
    "distinct_producer": ("rows", "orders"),
    "qualify_producer": ("rows", "orders"),
    "grouped": ("rows", "orders"),
    "nullable_asc": ("rows",),
    "nullable_desc": ("rows",),
    "filtered": ("rows", "orders"),
    "imported_source": ("rows", "orders"),
}
_REAL: dict[str, tuple] = {}


def _contract(names, *, parameters=False, library=False, changes=None):
    document = json.loads(collecting.contract(parameters=parameters, library=library))
    document["sources"] = [
        s for s in document["sources"] if s["selector"]["name"] in names
    ]
    for source in document["sources"]:
        for item in source["fields"]:
            item["representation"] = (changes or {}).get(
                item["name"], item["representation"]
            )
    return document


def _emitted(directory, files, document, policy="preserve"):
    """The live artifact of `result`, through the command's own composition."""
    root = project(directory, files)
    (root / "contract.json").write_text(json.dumps(document), encoding="utf-8")
    outcome, _ = emit_project(
        root,
        "main.pietto",
        "query",
        "result",
        "postgres",
        "contract.json",
        POLICIES[policy],
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None, outcome
    return outcome.artifact


def _files(shape):
    if shape in SHAPES:
        return {"main.pietto": HEAD.format(target="postgres") + SHAPES[shape]}
    return collecting.wired_files(shape)


def _loaded(build):
    return load_compiled(
        build.payload,
        expected_pin=build.pin,
        accepted_producer=build.producer,
        accepted_compatibility=build.compatibility,
    )


def _slots(root):
    return tuple(
        root.records[r.get("literal")].get("value").value
        for r in root.description.records
        if r.address.kind == "slot"
    )


def _real(factory, shape):
    """One admitted shape: its live artifact, build, loaded root and lowering."""
    if shape not in _REAL:
        names = REAL[shape]
        artifact = _emitted(
            factory.mktemp(shape) / "project",
            _files(shape),
            _contract(names, library=shape == "imported_source"),
        )
        build = build_compiled(artifact)
        loaded = _loaded(build)
        _REAL[shape] = (artifact, build, loaded, emit_compiled(loaded, ()))
    return _REAL[shape]


def _units(query):
    return getattr(query, "units", None) or query.bodies


def _collect_columns(artifact):
    return [
        column
        for unit in _units(artifact.ast)
        for column in unit.columns
        if type(column) is nested.CollectColumn
    ]


def _lateral(column):
    lateral = column.lateral
    return (
        column.label,
        column.carriers[0][:2],
        tuple(c[:2] for c in column.carriers[1:]),
        tuple(a[1:] for a in lateral.arrays),
        lateral.symbol.name,
        lateral.target.symbol.name,
        None if lateral.wrapper is None else lateral.wrapper.name,
        tuple((k[1], k[2]) for k in lateral.ordinal.keys),
        lateral.ordinal.symbol.name,
        lateral.sources,
    )


def _shape(contract):
    def leaf(field):
        return (
            field.ordinal,
            field.label,
            field.shape.canonical.name,
            field.nullability.value,
            None if field.meaning is None else field.meaning.law,
        )

    return [
        (
            f.ordinal,
            f.label,
            f.nullability.value,
            tuple(leaf(c) for c in f.shape.fields),
        )
        if type(f.shape) is NestedShape
        else leaf(f)
        for f in contract.shape.fields
    ]


def _contract_of(artifact):
    return build_result_contract(
        artifact.request.verification, scalar_meaning=artifact.request.scalar_meaning
    )


@pytest.mark.parametrize("shape", sorted(REAL))
def test_each_admitted_collect_shape_lowers_to_the_live_statement(
    tmp_path_factory, shape
):
    artifact, build, loaded, lowered = _real(tmp_path_factory, shape)
    plan = artifact.request.plan
    records = loaded.records
    # D-S09-1: one Collect operation and one block use per read; the use names
    # the let's ordered terminal result unit and no column.
    blocks = [
        r
        for r in records.values()
        if r.address.kind == "expression_block_use"
        and records[r.get("operation")].get("operator") == COLLECT_OPERATOR
    ]
    assert len(blocks) == len(plan.collects) > 0
    for block in blocks:
        unit = records[block.get("producer")]
        assert block.get("column") is None
        assert unit.address.kind == "result" and unit.get("ordering")
        assert records[unit.get("owner")].get("let") is not None
        assert records[block.get("consumer")].get("stage") == "projection"
        (port,) = (
            r
            for r in records.values()
            if r.address.kind == "port" and r.get("source") == block.get("operation")
        )
        assert port.get("logical") == ("collection", "non_null")
    assert not any(
        word in build.payload for word in (b"nested_relation", b"<nested relation>")
    )
    # SF1: the same bytes from the bundle alone, on a new root.
    assert loaded is not build.root
    assert lowered.rendered.sql == artifact.rendered.sql
    # The Collect's own generated requirements (flat stage carriers may differ
    # in kind between the live and the compiled lowering, not in bytes).
    assert [
        (g.kind, g.rule)
        for g in lowered.generated_requirements
        if g.kind.startswith("collect_")
    ] == [
        (g.kind, g.rule)
        for g in artifact.generated_requirements
        if g.kind.startswith("collect_")
    ]
    assert [o.rule for o in lowered.original_requirements] == [
        o.rule for o in artifact.original_requirements
    ]
    # SF2/SF4: each lateral, its carriers and its ordinal's ORDER items (the
    # hidden keys kept in the bundle) are the live ones.
    assert [_lateral(c) for c in _collect_columns(lowered)] == [
        _lateral(c) for c in _collect_columns(artifact)
    ]
    # SF3: the compiled authority's nested contract is the live one, and the
    # live-built root and the loaded root have one v2 digest.
    live, compiled = _contract_of(artifact), _contract_of(lowered)
    assert _shape(compiled) == _shape(live)
    assert contract_digest(compiled) == contract_digest(
        _contract_of(emit_compiled(build.root, ()))
    )
    # AC-S09-10: each compiled nested port carries the live S04 descriptor.
    assert [
        p.field.evidence.resolved_type
        for p in lowered.request.plan.exports
        if p.field.evidence.resolved_type.kind
        is ProjectResolvedTypeKind.NESTED_RELATION
    ] == [
        p.field.evidence.resolved_type
        for p in plan.exports
        if p.field.evidence.resolved_type.kind
        is ProjectResolvedTypeKind.NESTED_RELATION
    ]


@pytest.mark.parametrize(
    "program",
    [p.name for p in oracle.programs() if isinstance(p.spec, oracle.Collect)],
)
def test_every_literal_oracle_collect_program_lowers_source_free(tmp_path, program):
    item = oracle.program(program)
    text = "".join(t for _, t in item.files)
    document = json.loads(collecting.oracle_contract())
    document["sources"] = [
        s for s in document["sources"] if f"from {s['selector']['name']}" in text
    ]
    for policy in ("preserve", "bind-safe"):
        artifact = _emitted(tmp_path / policy, dict(item.files), document, policy)
        loaded = _loaded(build_compiled(artifact))
        lowered = emit_compiled(loaded, _slots(loaded))
        assert lowered.rendered.sql == artifact.rendered.sql
        assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))


# A captured let with its own literals between a parent WHERE literal and
# literal columns around the Collect; and header parameters on both sides.
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
        recent_orders = collect recent
"""


def test_bundle_parameters_keep_the_live_native_order(tmp_path):
    for name, body, policy in (
        ("bind", BIND_SAFE, "bind-safe"),
        ("header", HEADER, "preserve"),
    ):
        artifact = _emitted(
            tmp_path / name,
            {"main.pietto": HEAD.format(target="postgres") + body},
            json.loads(collecting.contract(parameters=True)),
            policy,
        )
        loaded = _loaded(build_compiled(artifact))
        values = _slots(loaded)
        lowered = emit_compiled(loaded, values)
        assert lowered.rendered.sql == artifact.rendered.sql
        assert [
            (u.ordinal, u.server_index, u.physical_type) for u in lowered.parameter_uses
        ] == [
            (u.ordinal, u.server_index, u.physical_type)
            for u in artifact.parameter_uses
        ]
        if values:
            # A fresh binding re-derives the lateral's own literals as well.
            other = emit_compiled(loaded, tuple(v + 1 for v in values))
            assert other.rendered.sql == artifact.rendered.sql
            assert [f.value for f in other.fixed_values] == [v + 1 for v in values]
        else:
            # Each binding of the header reads the let's parameter in its lateral.
            bound = emit_compiled(loaded, values, (7, 1))
            assert bound.rendered.sql == artifact.rendered.sql


DECIMAL = {
    "storage": {"kind": "pg_numeric", "precision": 9, "scale": 2},
    "nullable": False,
    "domain": {"kind": "decimal", "precision": 9, "scale": 2},
}
TIMESTAMP = {
    "storage": {"kind": "pg_timestamp", "fractional_seconds": 6},
    "nullable": False,
    "domain": {"kind": "timestamp"},
}
CHILDREN = """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            id
            total
            created_at
        order by id desc
    from rows
    select:
        id
        recent_orders = collect recent
"""


def test_decimal_and_timestamp_children_round_trip_with_their_meaning(tmp_path):
    head = (
        HEAD.format(target="postgres")
        .replace("    total: Int\n", "    total: Decimal(9, 2)\n")
        .replace("    created_at: Int\n", "    created_at: Timestamp\n")
    )
    artifact = _emitted(
        tmp_path / "children",
        {"main.pietto": head + CHILDREN},
        _contract(
            ("rows", "orders"),
            changes={"total": DECIMAL, "created_at": TIMESTAMP},
        ),
    )
    build = build_compiled(artifact)
    lowered = emit_compiled(_loaded(build), ())
    assert lowered.rendered.sql == artifact.rendered.sql
    compiled = _contract_of(lowered)
    assert _shape(compiled) == _shape(_contract_of(artifact))
    (_, recent) = compiled.shape.fields
    assert type(recent.shape) is NestedShape
    assert [
        (c.label, getattr(c.shape, "canonical").name, c.meaning is None)
        for c in recent.shape.fields
    ] == [
        ("id", "Int", True),
        ("total", "Decimal", True),
        ("created_at", "Timestamp", False),
    ]
    assert contract_digest(compiled) == contract_digest(
        _contract_of(emit_compiled(build.root, ()))
    )


PINNED = """query result:
    let recent:
        capture rows
        from orders
        where orders.customer_id == rows.id
        select:
            id
            total
        order by created_at desc, id
        limit 2
    let other:
        capture rows
        from orders
        where orders.id == rows.id
        select:
            id
            total
        order by created_at desc, id
        limit 2
    from rows
    select:
        id
        first = collect recent
        second = collect other
"""
FIRST = "order by created_at desc, id\n        limit 2\n    let"


def test_the_pin_binds_the_childrens_order_owner_and_limit(tmp_path):
    """AC-S09-08: what the v2 digest leaves to the pin is in the pinned records:
    only the first field's child order direction or key, its collected let
    (the same child schema) or its LIMIT differs."""
    variants = {
        "base": PINNED,
        "direction": PINNED.replace(FIRST, FIRST.replace("desc, id", "asc, id")),
        "key": PINNED.replace(FIRST, FIRST.replace("created_at desc", "total desc")),
        "owner": PINNED.replace(
            "first = collect recent", "first = collect other"
        ).replace("second = collect other", "second = collect recent"),
        "limit": PINNED.replace(FIRST, FIRST.replace("limit 2", "limit 3")),
    }
    assert len(set(variants.values())) == len(variants)
    built, digests = {}, {}
    for name, body in variants.items():
        artifact = _emitted(
            tmp_path / name,
            {"main.pietto": HEAD.format(target="postgres") + body},
            _contract(("rows", "orders")),
        )
        built[name] = build_compiled(artifact)
        digests[name] = contract_digest(
            _contract_of(emit_compiled(_loaded(built[name]), ()))
        )
    assert len({b.pin for b in built.values()}) == len(variants)
    assert len(set(digests.values())) == len(variants)
    again = build_compiled(
        _emitted(
            tmp_path / "again",
            {"main.pietto": HEAD.format(target="postgres") + PINNED},
            _contract(("rows", "orders")),
        )
    )
    assert (again.payload, again.pin) == (built["base"].payload, built["base"].pin)
    assert (
        contract_digest(_contract_of(emit_compiled(again.root, ()))) == digests["base"]
    )


def _damaged(description, change):
    records = _records(description)
    uses = sorted(
        (
            r
            for r in records.values()
            if r.address.kind == "expression_block_use"
            and records[r.get("operation")].get("operator") == COLLECT_OPERATOR
        ),
        key=lambda r: r.address.position,
    )
    first = uses[0]
    unit = records[first.get("producer")]
    operation = records[first.get("operation")]
    (port,) = (
        r
        for r in records.values()
        if r.address.kind == "port" and r.get("source") == operation.address
    )
    if change == "producer_projection_row":
        return _changed(description, _set(first, producer=unit.get("input")))
    if change == "column":
        return _changed(description, _set(first, column=0))
    if change == "ordering":
        return _changed(description, _set(unit, ordering=()))
    if change == "logical":
        return _changed(description, _set(operation, logical=("Int", "non_null")))
    if change == "operand":
        literal = next(a for a in records if a.kind == "literal")
        return _changed(description, _set(operation, operands=(literal,)))
    if change == "port":
        return _changed(description, _set(port, logical=("collection", "nullable")))
    if change == "output":
        (output,) = (
            r
            for r in records.values()
            if r.address.kind == "output" and r.get("port") == port.address
        )
        return _changed(description, _set(output, logical=("Int", "non_null")))
    if change == "second_reader":
        return _changed(description, _set(uses[1], producer=first.get("producer")))
    if change == "capture":
        (capture, *_) = (r for r in records.values() if r.address.kind == "capture_use")
        return dataclasses.replace(
            description,
            members=tuple(
                (name, tuple(r for r in group if r.address != capture.address))
                for name, group in description.members
            ),
        )
    assert change == "children"
    return _changed(
        description,
        _set(
            unit,
            outputs=tuple(reversed(unit.get("outputs"))),
            projection=tuple(reversed(unit.get("projection"))),
        ),
    )


@pytest.mark.parametrize(
    ("shape", "change", "category"),
    (
        ("top_k", "producer_projection_row", "COMPILED_EXPRESSION_BLOCK_USE"),
        ("top_k", "column", "COMPILED_EXPRESSION_BLOCK_USE"),
        ("top_k", "ordering", "COMPILED_EXPRESSION_BLOCK_USE"),
        ("closed", "ordering", "COMPILED_RESULT_BOUNDARIES"),
        ("top_k", "logical", "COMPILED_COLLECT_LOGICAL"),
        ("top_k", "operand", "COMPILED_OPERATOR_ARITY"),
        ("top_k", "port", "COMPILED_OUTPUT_PORT"),
        ("ordered_parent", "port", "COMPILED_COLLECTION_PORT"),
        ("top_k", "output", "COMPILED_OUTPUT_PORT"),
        ("parallel", "second_reader", "COMPILED_RELATION_INVENTORY_CLOSURE"),
        ("top_k", "capture", "COMPILED_INLINE_INVENTORY"),
        ("top_k", "children", "COMPILED_COLLECT_CHILDREN_DRIFT"),
    ),
)
def test_a_damaged_real_collect_bundle_is_refused_before_any_connection(
    tmp_path_factory, shape, change, category
):
    """AC-S09-09: each damage, pinned again, is refused at load or lowering."""
    _, build, _, _ = _real(tmp_path_factory, shape)
    raw = encode(_damaged(build.root.description, change))
    before = set(sys.modules)
    with pytest.raises(CompiledError) as caught:
        emit_compiled(_load(build, raw), ())
    assert str(caught.value) == category
    assert not {m for m in set(sys.modules) - before if m.split(".")[0] in DRIVERS}


def test_compiled_facts_ir_and_plan_carry_the_collect_explicitly(tmp_path_factory):
    """AC-S09-10: only a Collect and the ports and reads carrying it have a
    nested fact; a scalar reader of one refuses, and the compiled plan's
    Collect records are checked against their own records."""
    _, _, loaded, lowered = _real(tmp_path_factory, "parallel")
    plan = lowered.request.plan
    records = loaded.records
    facts = plan.ir.completed.facts
    collects = {
        r.address
        for r in records.values()
        if r.address.kind == "operation" and r.get("operator") == COLLECT_OPERATOR
    }
    carriers = {
        r.address
        for r in records.values()
        if r.address.kind == "port" and r.get("source") in collects
    }
    carriers |= {
        r.address
        for r in records.values()
        if r.address.kind in ("read", "port")
        and r.get("port" if r.address.kind == "read" else "source") in carriers
    }
    carriers |= {
        r.address
        for r in records.values()
        if r.address.kind == "port" and r.get("source") in carriers
    }
    assert {f.address for f in facts if f.nested is not None} == collects | carriers
    for fact in facts:
        if fact.nested is None:
            continue
        assert fact.realization is None
        assert fact.value_type.resolved_type.name == "<nested relation>"
        with pytest.raises(CompiledError, match="^COMPILED_LOGICAL_ONLY_FACT$"):
            fact.require_realization()
    assert len(plan.collects) == 2
    first, second = plan.collects
    other = _real(tmp_path_factory, "closed")[3].request.plan.collects[0]
    for damaged in ((), (first,), (first, first), (second, first), (other, second)):
        with pytest.raises(CompiledError, match="^COMPILED_PLAN_COLLECT"):
            verify_compiled_sql_plan(dataclasses.replace(plan, collects=damaged))
    # No scalar reader is open to a nested export yet: it refuses explicitly.
    with pytest.raises(ResultError, match="^NESTED_UNAVAILABLE$"):
        from pietto._project.project_result_contract import scalar_fields

        scalar_fields(_contract_of(lowered))


def test_the_public_face_still_refuses_a_nested_query_before_connecting(
    tmp_path_factory, tmp_path
):
    """AC-S09-11: the template gate (S12 opens it) refuses a nested query and
    a privately built nested bundle with PIE-R1004 before any connection."""
    _, build, _, _ = _real(tmp_path_factory, "top_k")
    before = set(sys.modules)
    with pytest.raises(execution.RequestRejected) as loaded:
        execution.load_bundle(
            build.payload,
            expected_pin=build.pin,
            accepted_producer=build.producer,
            accepted_compatibility=build.compatibility[4],
        )
    root = project(tmp_path / "public", _files("top_k"))
    (root / "contract.json").write_text(
        json.dumps(_contract(REAL["top_k"])), encoding="utf-8"
    )
    with pytest.raises(execution.RequestRejected) as compiled:
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="result",
            dialect="postgres",
            emission_contract="contract.json",
        )
    for caught in (loaded, compiled):
        assert (caught.value.code, caught.value.detail) == (
            "PIE-R1004",
            "NESTED_UNAVAILABLE",
        )
        assert caught.value.attempt is None and caught.value.outcome is None
    assert not {m for m in set(sys.modules) - before if m.split(".")[0] in DRIVERS}


def test_a_nested_bundle_lowers_without_any_source_entry(
    tmp_path_factory, tmp_path, monkeypatch
):
    """SF5: the bundle bytes and the caller's three records alone."""
    import pietto.parser_api as parser
    from pietto._project import check, model, project_completed_semantics

    artifact, build, _, _ = _real(tmp_path_factory, "top_k")

    def forbidden(*args, **kwargs):
        raise AssertionError("source-language entry reached from a bundle")

    original_read = Path.read_bytes

    def closed_read(path):
        assert path.suffix != ".pietto" and path.name != "pietto.toml"
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", closed_read)
    monkeypatch.setattr(parser, "parse_source", forbidden)
    monkeypatch.setattr(check, "check_project_parse_only", forbidden)
    monkeypatch.setattr(model, "build_empty_project_semantic_result", forbidden)
    monkeypatch.setattr(
        project_completed_semantics,
        "build_project_completed_semantic_result",
        forbidden,
    )
    monkeypatch.chdir(tmp_path)
    lowered = emit_compiled(_loaded(build), ())
    assert lowered.rendered.sql == artifact.rendered.sql
    assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
