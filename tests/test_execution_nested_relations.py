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
from _pietto_plan_nested import (
    HEAD,
    NESTED_KEY_READERS,
    SHAPES,
    keyed_sources,
    project,
    retained_unnest_sources,
    retained_unnest_contract,
)
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
    collection_source,
    decode,
    encode,
    selected_relations,
)
from pietto._project.project_compiled_verification import (
    RELATIONS,
    verify_description,
)
from pietto._project.project_execution_binding_verification import native_arguments
from pietto._project.project_execution_template import (
    bind_values,
    prepare_live_template,
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
def test_an_unbound_unnest_record_decodes_and_is_refused(built, place, count):
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
    category = "COMPILED_RECORD_ORDER" if member == "outputs" else "COMPILED_UNNEST"
    assert _refused(forged).startswith(category)
    with pytest.raises(CompiledError, match="^" + category):
        _load(build, raw)
    before = set(sys.modules)
    with pytest.raises(execution.RequestRejected) as caught:
        execution.load_bundle(
            raw,
            expected_pin=content_pin(raw),
            accepted_producer=build.producer,
            accepted_compatibility=build.compatibility[4],
        )
    assert caught.value.code == "PIE-R1008"
    assert isinstance(caught.value.detail, str)
    assert caught.value.detail.startswith(category)
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
    # A JOIN value admits no operation at all.
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
    # A named reader may select the exact collection again (S16).
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
    verify_description(_changed(description, *again))


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
    # A scalar JOIN input cannot acquire a collection logical.
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
    assert outcome.status == "VERIFIED" and outcome.artifact is not None, [
        (blocker.code, blocker.detail) for blocker in outcome.blockers
    ]
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


_UNNEST_REAL: dict[str, tuple] = {}


def _unnest_real(tmp_path, name):
    """One U1/U2/U4 literal program through build, load and compiled lowering."""
    if name not in _UNNEST_REAL:
        item = oracle.program(name)
        text = "".join(value for _, value in item.files)
        document = json.loads(collecting.oracle_contract())
        document["sources"] = [
            source
            for source in document["sources"]
            if f"from {source['selector']['name']}" in text
        ]
        artifact = _emitted(tmp_path / name, dict(item.files), document)
        build = build_compiled(artifact)
        loaded = _loaded(build)
        _UNNEST_REAL[name] = (artifact, build, loaded, emit_compiled(loaded, ()))
    return _UNNEST_REAL[name]


@pytest.mark.parametrize(
    "leaves",
    (
        ("Int", "Float", "Decimal"),
        ("Int", "Date", "Timestamp", "UUID"),
    ),
)
def test_opened_unnest_leaves_build_load_lower_and_reject_tampering(tmp_path, leaves):
    item = oracle.program(
        "U1_cross" if "Decimal" in leaves else "U2_inner_true", leaves
    )
    text = "".join(value for _, value in item.files)
    document = json.loads(collecting.oracle_contract(leaves))
    document["sources"] = [
        source
        for source in document["sources"]
        if f"from {source['selector']['name']}" in text
    ]
    artifact = _emitted(tmp_path / "opened", dict(item.files), document)
    build = build_compiled(artifact)
    loaded = _loaded(build)
    lowered = emit_compiled(loaded, ())
    assert lowered.rendered.sql == artifact.rendered.sql
    assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
    records = _records(build.root.description)
    (unnest,) = (
        record for record in records.values() if record.address.kind == "unnest"
    )
    fields = tuple(records[address] for address in unnest.get("fields"))
    if "Decimal" in leaves:
        (decimal,) = (field for field in fields if field.get("logical")[0] == "Decimal")
        damages = (_set(decimal, decimal=(38, decimal.get("decimal")[1])),)
    else:
        temporal = tuple(
            field
            for field in fields
            if field.get("logical")[0] in {"Timestamp", "UUID"}
        )
        assert len(temporal) == 2
        damages = tuple(_set(field, meaning=None) for field in temporal)
    for damaged in damages:
        with pytest.raises(CompiledError):
            _load(build, encode(_changed(build.root.description, damaged)))


_S16_REAL: dict[tuple[str, bool], tuple] = {}


def _s16_real(tmp_path, retained="sibling", filtered=False):
    key = (retained, filtered)
    if key not in _S16_REAL:
        contract = retained_unnest_contract()
        files = retained_unnest_sources()
        files["main.pietto"] = files["main.pietto"].replace(
            "retained = p.sibling", f"retained = p.{retained}"
        )
        if filtered:
            files["main.pietto"] = files["main.pietto"].replace(
                "    select:\n", "    where child.id > 0\n    select:\n"
            )
        artifact = _emitted(
            tmp_path / "s16",
            files,
            contract,
        )
        build = build_compiled(artifact)
        loaded = _loaded(build)
        _S16_REAL[key] = artifact, build, loaded, emit_compiled(loaded, ())
    return _S16_REAL[key]


def _unnest_damage(description, change):
    records = _records(description)
    (unnest,) = (
        record for record in records.values() if record.address.kind == "unnest"
    )
    owner, _position, source, fields, outputs, layout = unnest.values
    join = records[layout[2]]
    left, right = (records[address] for address in join.get("inputs"))
    if change == "owner":
        foreign = next(
            record.address
            for record in records.values()
            if record.address.kind == "declaration" and record.address != owner
        )
        return _changed(description, _set(unnest, owner=foreign))
    if change == "source":
        foreign = next(port for port in left.get("ports") if port != source)
        return _changed(description, _set(unnest, source=foreign))
    if change == "fields":
        return _changed(description, _set(unnest, fields=tuple(reversed(fields))))
    if change == "logical":
        field = records[fields[0]]
        return _changed(description, _set(field, logical=("Float", "non_null")))
    if change == "outputs":
        return _changed(description, _set(unnest, outputs=tuple(reversed(outputs))))
    if change == "layout":
        return _changed(description, _set(unnest, layout=(*layout[:3], 0, None)))
    if change == "wrong_left":
        return _changed(description, _set(join, inputs=(right.address, left.address)))
    if change == "wrong_join":
        return _changed(
            description,
            _set(unnest, layout=(layout[0], layout[1], left.address, *layout[3:])),
        )
    assert change == "coordinated_children"
    pairs = tuple(zip(fields, outputs, strict=True))[::-1]
    changed = [
        _set(
            unnest,
            fields=tuple(field for field, _ in pairs),
            outputs=tuple(output for _, output in pairs),
        ),
        _set(right, ports=tuple(output for _, output in pairs)),
    ]
    for ordinal, (field, output) in enumerate(pairs):
        changed.append(_set(records[output], ordinal=ordinal, source=field))
    return _changed(description, *changed)


@pytest.mark.parametrize(
    "name",
    (
        "U1_cross",
        "U2_inner_true",
        "U3_inner_v_gt_10",
        "U4_left_true",
        "U5_left_v_gt_10",
    ),
)
def test_literal_unnest_bundle_lowers_source_free(tmp_path, monkeypatch, name):
    """S13 keeps a flat public result while rebuilding its private right input."""
    artifact, build, _loaded_root, _lowered = _unnest_real(tmp_path, name)
    import pietto.parser_api as parser
    from pietto._project import check, model, project_completed_semantics

    def forbidden(*args, **kwargs):
        raise AssertionError("source-language entry reached from a bundle")

    monkeypatch.setattr(parser, "parse_source", forbidden)
    monkeypatch.setattr(check, "check_project_parse_only", forbidden)
    monkeypatch.setattr(model, "build_empty_project_semantic_result", forbidden)
    monkeypatch.setattr(
        project_completed_semantics,
        "build_project_completed_semantic_result",
        forbidden,
    )
    loaded = _loaded(build)
    lowered = emit_compiled(loaded, ())
    assert lowered.rendered.sql == artifact.rendered.sql
    assert not any(
        type(field.shape) is NestedShape for field in _contract_of(lowered).shape.fields
    )
    assert len(lowered.request.plan.unnests) == 1
    verify_compiled_sql_plan(lowered.request.plan)


@pytest.mark.parametrize("retained", ("sibling", "nested"))
def test_s16_compiled_retained_unnest_lowers_source_free(
    tmp_path, monkeypatch, retained
):
    """A renamed imported parent keeps its Collect authority after source removal."""

    artifact, build, _loaded_root, _lowered = _s16_real(tmp_path, retained)
    import pietto.parser_api as parser
    from pietto._project import check, model, project_completed_semantics

    def forbidden(*args, **kwargs):
        raise AssertionError("source-language entry reached from a bundle")

    monkeypatch.setattr(parser, "parse_source", forbidden)
    monkeypatch.setattr(check, "check_project_parse_only", forbidden)
    monkeypatch.setattr(model, "build_empty_project_semantic_result", forbidden)
    monkeypatch.setattr(
        project_completed_semantics,
        "build_project_completed_semantic_result",
        forbidden,
    )
    lowered = emit_compiled(_loaded(build), ())
    plan = lowered.request.plan
    (unnest,) = plan.unnests
    assert lowered.rendered.sql == artifact.rendered.sql
    assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
    assert unnest.collect in plan.references.values()
    origin = collection_source(
        plan.ir.completed.root.records,
        Address(unnest.source.kind, unnest.source.position),
    )
    assert origin is not None and plan.references[origin.address] is unnest.collect
    verify_compiled_sql_plan(plan)


@pytest.mark.parametrize("change", ("source", "wrong_left"))
def test_s16_compiled_foreign_or_missing_unnest_anchor_is_refused(tmp_path, change):
    """A substituted collection source is rejected by the existing reader."""

    _artifact, build, _loaded_root, _lowered = _s16_real(tmp_path)
    raw = encode(_unnest_damage(build.root.description, change))
    with pytest.raises(CompiledError):
        _load(build, raw)


@pytest.mark.parametrize(
    "change",
    (
        "owner",
        "source",
        "fields",
        "logical",
        "outputs",
        "layout",
        "wrong_left",
        "wrong_join",
        "coordinated_children",
    ),
)
def test_damaged_literal_unnest_bundle_is_refused_before_lowering(tmp_path, change):
    """Every v6 Unnest identity component is independently fail-closed."""
    _artifact, build, _loaded_root, _lowered = _unnest_real(tmp_path, "U1_cross")
    raw = encode(_unnest_damage(build.root.description, change))
    with pytest.raises(CompiledError):
        _load(build, raw)


def test_compiled_unnest_filter_after_join_preserves_retained_collection(tmp_path):
    artifact, build, _loaded_root, lowered = _s16_real(tmp_path, filtered=True)
    assert lowered.rendered.sql == artifact.rendered.sql
    assert b"WHERE" in lowered.rendered.sql
    assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
    verify_description(build.root.description)


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


# The per-group detail route: `by_key` groups a producer, and `result` reads it
# with `from` and collects a let that captures it and matches the key.
DETAIL = """shape Row:
    id: Int
    k: Int | None
    fk: Float | None
    v: Int
    pk = unique(id)
source src: Row = postgres.table("src")
query pos:
    from src
    where v > 0
    select:
        id
        k
        fk
        v
query by_key:
    from {producer}
    group by:
        {key}
    select:
        {key}
        n = count()
query result:
    let members:
        capture by_key
        from {reader}
        where {test}
        select:
            id
            {key}
        order by id
    from by_key
    select:
        {key}
        n
        items = collect members
"""
# Each route's producer, let input, key and correlation, and what PostgreSQL
# emits for it with literals preserved: `same_value` keeps a None key's rows
# where `==` matches none; the let reads the producer's own rows, or the raw
# source beside a filtered producer; each member keeps its own Float value.
DETAIL_ROUTES = {
    "same_value": (
        ("src", "src", "k", "same_value(src.k, by_key.k)"),
        'FROM "public"."src" AS "s1" WHERE ("s1"."k" IS NOT DISTINCT FROM "s2"."c0")',
    ),
    "equality": (
        ("src", "src", "k", "src.k == by_key.k"),
        'FROM "public"."src" AS "s1" WHERE ("s1"."k" = "s2"."c0")',
    ),
    "shared_filter": (
        ("pos", "pos", "k", "same_value(pos.k, by_key.k)"),
        'COUNT(*) AS "c1" FROM "p1" AS "s1" GROUP BY "s1"."c1"',
        'FROM "p1" AS "s2" WHERE ("s2"."c1" IS NOT DISTINCT FROM "s3"."c0")',
    ),
    "raw_source": (
        ("pos", "src", "k", "same_value(src.k, by_key.k)"),
        'COUNT(*) AS "c1" FROM "p1" AS "s1" GROUP BY "s1"."c1"',
        'FROM "public"."src" AS "s2" WHERE ("s2"."k" IS NOT DISTINCT FROM "s3"."c0")',
    ),
    "float_key": (
        ("src", "src", "fk", "same_value(src.fk, by_key.fk)"),
        '"s2"."c0" AS "fk", "s2"."c1" AS "n", "g0"."n" AS "items", '
        '"g0"."a0" AS "id", "g0"."a1" AS "fk" FROM "p1" AS "s2"',
        'FROM "public"."src" AS "s1" WHERE ("s1"."fk" IS NOT DISTINCT FROM "s2"."c0")',
    ),
}


def _detail_contract():
    document = _contract(("rows",), parameters=True)
    (source,) = document["sources"]
    source["selector"]["name"] = source["relation"]["name"] = "src"
    integer = source["fields"][0]["representation"]
    fields = {
        "id": integer,
        "k": {**integer, "nullable": True},
        "fk": {
            "storage": {"kind": "pg_float8"},
            "nullable": True,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
        "v": integer,
    }
    source["fields"] = [
        {"ordinal": i, "name": name, "column": name, "representation": value}
        for i, (name, value) in enumerate(fields.items())
    ]
    return document


@pytest.mark.parametrize("route", sorted(DETAIL_ROUTES))
def test_the_per_group_detail_route_lowers_and_binds_its_live_statement(
    tmp_path, route
):
    """Emission, the compiled bundle and the live template of each detail
    route render one statement and bind the emission's arguments."""
    (producer, reader, key, test), *emitted = DETAIL_ROUTES[route]
    files = {
        "main.pietto": DETAIL.format(
            producer=producer, reader=reader, key=key, test=test
        )
    }
    for policy in ("preserve", "bind-safe"):
        artifact = _emitted(tmp_path / policy, files, _detail_contract(), policy)
        sql = artifact.rendered.sql
        assert policy != "preserve" or all(f.encode() in sql for f in emitted)
        loaded = _loaded(build_compiled(artifact))
        assert emit_compiled(loaded, _slots(loaded)).rendered.sql == sql
        operators = {
            r.get("operator")
            for r in loaded.records.values()
            if r.address.kind == "operation"
        }
        assert (("scalar_call", "same_value") in operators) is (route != "equality")
        template = prepare_live_template(artifact)
        values = tuple(v.value for v in artifact.fixed_values)
        bound = bind_values(template, tuple(zip(template.slots, values, strict=True)))
        assert template.artifact.rendered.sql == bound.artifact.rendered.sql == sql
        assert bound.arguments == native_arguments(artifact, values)


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


@pytest.mark.parametrize("shape", ("top_k", "ordered_parent"))
def test_public_nested_queries_and_bundles_prepare_without_connecting(
    tmp_path_factory, tmp_path, shape
):
    """S12 opens templates; execution route/leaf/source admission remains separate."""
    _, build, _, _ = _real(tmp_path_factory, shape)
    before = set(sys.modules)
    loaded = execution.load_bundle(
        build.payload,
        expected_pin=build.pin,
        accepted_producer=build.producer,
        accepted_compatibility=build.compatibility[4],
    )
    root = project(tmp_path / "public", _files(shape))
    (root / "contract.json").write_text(
        json.dumps(_contract(REAL[shape])), encoding="utf-8"
    )
    compiled = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
    )
    assert (compiled.origin, loaded.origin) == ("live", "bundle")
    for query in (compiled, loaded):
        handle = execution.execute(
            query,
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 9, "phase66", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(("public", "pg_catalog")),
        )
        try:
            assert handle.outcome.end == "NOT_STARTED"
        finally:
            handle.close()
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


def test_grouped_parameter_filter_retains_sibling_after_source_free_unnest(tmp_path):
    from _pietto_execution_api import write_grouped_composed_nested

    root = write_grouped_composed_nested(tmp_path / "authored")
    files = {path.name: path.read_text() for path in root.glob("*.pietto")}
    contract = json.loads((root / "contract.json").read_text())
    artifact = _emitted(tmp_path / "source", files, contract)
    loaded = _loaded(build_compiled(artifact))
    for cutoff in (1, 2):
        lowered = emit_compiled(loaded, (), (cutoff,))
        assert lowered.rendered.sql == artifact.rendered.sql
        assert [use.server_index for use in lowered.parameter_uses] == [1]
        assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
    assert b"GROUP BY" in artifact.rendered.sql
    assert b"$1" in artifact.rendered.sql


# The collected child of a nested key: its type and contract representation.
_KEY_CHILDREN = {
    "int": ("Int", None),
    "decimal": (
        "Decimal(18, 4) | None",
        {
            "storage": {"kind": "pg_numeric", "precision": 18, "scale": 4},
            "nullable": True,
            "domain": {"kind": "decimal", "precision": 18, "scale": 4},
        },
    ),
    "float": (
        "Float | None",
        {
            "storage": {"kind": "pg_float8"},
            "nullable": True,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
    ),
}


@pytest.mark.parametrize("child", sorted(_KEY_CHILDREN))
@pytest.mark.parametrize("reader", sorted(NESTED_KEY_READERS))
def test_a_nested_key_bundle_lowers_to_the_live_statement(tmp_path, reader, child):
    # D73.05: a nested GROUP BY key is an aggregate's key and output, a
    # nested DISTINCT field a DISTINCT result's read; both lower source free,
    # whatever the type of the collected child.
    written, representation = _KEY_CHILDREN[child]
    artifact = _emitted(
        tmp_path / reader,
        keyed_sources(reader, child=written),
        _contract(
            ("rows", "orders"),
            changes=None if representation is None else {"total": representation},
        ),
    )
    build = build_compiled(artifact)
    loaded = _loaded(build)
    lowered = emit_compiled(loaded, ())
    assert loaded is not build.root
    assert lowered.rendered.sql == artifact.rendered.sql
    assert _shape(_contract_of(lowered)) == _shape(_contract_of(artifact))
    assert contract_digest(_contract_of(lowered)) == contract_digest(
        _contract_of(emit_compiled(build.root, ()))
    )
    records = loaded.records
    collections = {
        r.address
        for r in records.values()
        if r.address.kind == "port" and r.get("logical")[:1] == ("collection",)
    }
    if reader == "group":
        (aggregate,) = (r for r in records.values() if r.address.kind == "aggregate")
        assert aggregate.get("mode") == "grouped"
        (key,) = aggregate.get("keys")
        assert records[key].get("port") in collections
    else:
        (result,) = (
            r
            for r in records.values()
            if r.address.kind == "result" and r.get("distinct")
        )
        assert any(
            records[records[p].get("source")].get("port") in collections
            for p in result.get("outputs")
        )
    verify_description(build.root.description)
