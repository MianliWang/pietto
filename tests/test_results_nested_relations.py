"""Phase71 S07: one-level nested result contracts, their closed v2 document and
explicit refusal by every reader that is still flat.

The closed-schema tests write v2 documents by hand from real flat v1
documents; the build, verify, writer and correspondence tests use real nested
programs built through the IR and plan builders.
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from _pietto_execution_jobs_probe import compiled_template
import _pietto_results_nested as nested_helper
import _pietto_results_product as probe
from pietto._project import project_job_delivery as delivery
from pietto._project import project_result_binding as p
from pietto._project import project_result_contract as c
from pietto._project import project_result_contract_correspondence as runtime
from pietto._project import project_result_contract_portable as writer
from pietto._project import project_result_contract_pure_boundary as pure
from pietto._project import project_result_ipc as ipc
from pietto._project import project_result_output as o
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.project_execution import PostgresAccess, prepare_execution
from pietto._project.project_execution_reader import (
    bind_native_output,
    bind_native_projection,
    bind_postgres_output,
    bind_stored_output,
    decode_native_rows,
)
from pietto._project.project_scalar_meaning import acquire_scalar_meaning
from pietto._project.project_sql_plan_verification import CompiledSQLPlanVerification

pytestmark = pytest.mark.ci_workload("general-runtime")

BASE = """type Code = Text
type Note = Text
shape Row:
    id: Int
    created: Int
    note: Note | None
    amount: Decimal(18, 4)
    stamp: Timestamp
    later: Timestamp | None
    code: Code
source rows: Row = postgres.table("rows")
table result:
    from rows
    select:
        id
        note
        amount
        stamp
        later
        code
    order by created desc, id
"""
LET = {
    "identity": {
        "module": "main.pietto",
        "namespace": "relation",
        "kind": "query",
        "name": "recent",
    },
    "module_position": 0,
    "declaration_position": 4,
    "let_position": 0,
}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """A real flat root with aliases, Decimal, meaning and a hidden order key."""
    checked = probe.build_neutral(
        tmp_path_factory.mktemp("nested-base") / "base", {"main.pietto": BASE}
    )
    contract = c.build_result_contract(
        checked, scalar_meaning=acquire_scalar_meaning(checked)
    )
    return checked, contract


@pytest.fixture(scope="module")
def flat(base):
    checked, contract = base
    return writer.export_result_contract(contract, checked).view.document


def nested(flat, let=LET):
    """Keep the first flat leaf; collect all flat leaves under one let."""
    doc = deepcopy(flat)
    children = doc["fields"]
    element_output = {
        "kind": "relation_output",
        "position": 40,
        "producer": 41,
        "owner": let,
        "field_count": len(children),
    }
    for child in children:
        child["identity"]["owner"] = let
        child["output"] = element_output
        child["port"]["owner"] = {"kind": "definition", "position": 0}
        child["port"]["coordinate"]["position"] += 10
    doc["ordering"]["owner"] = let
    doc["output"]["field_count"] = 2
    top = deepcopy(flat["fields"][0])
    top.update(output=doc["output"])
    collection = {
        "ordinal": 1,
        "label": "recent",
        "identity": {
            "owner": doc["owner"],
            "kind": "relation_output",
            "position": 1,
            "name": "recent",
        },
        "port": {
            "coordinate": {"kind": "export", "position": 1},
            "owner": top["port"]["owner"],
            "producer": None,
        },
        "output": doc["output"],
        "position": 1,
        "kind": "collection",
        "element": {
            "owner": let,
            "output": element_output,
            "multiplicity": "bag",
            "nullability": "non_null",
            "ordering": doc["ordering"],
            "field_count": len(children),
            "fields": children,
        },
        "nullability": "non_null",
        "declared_nullability": "non_null",
        "role": "ordinary_row_value",
        "provenance": {
            "kind": "derived_expression",
            "symbol": None,
            "location": {
                "path": "main.pietto",
                "line": 14,
                "column": 9,
                "end_line": 14,
                "end_column": 30,
            },
        },
    }
    doc.update(
        format=pure.FORMAT_V2, field_count=2, fields=[top, collection], ordering=None
    )
    # Separate every shared record, as a decoded document has them.
    return json.loads(json.dumps(doc))


def test_hand_built_v2_round_trips_as_canonical_bytes(flat):
    assert [f["label"] for f in flat["fields"]] == [
        "id",
        "note",
        "amount",
        "stamp",
        "later",
        "code",
    ]
    assert [t["owner"]["identity"]["name"] for t in flat["types"]] == ["Note", "Code"]
    doc = nested(flat)
    data = pure.encode_document(doc)
    assert data == pure._canonical(doc)
    view = pure.decode_contract(data)
    assert view.document == doc
    assert pure.reencode_contract(view) == data
    element = view.fields[1]["element"]
    assert [f["label"] for f in element["fields"]] == [
        "id",
        "note",
        "amount",
        "stamp",
        "later",
        "code",
    ]
    assert element["ordering"]["keys"][0]["expression"]["name"] == "created"
    assert [f.get("meaning") for f in element["fields"]] == [
        None,
        None,
        None,
        0,
        1,
        None,
    ]
    assert b"nested_relation" not in data and b"<nested relation>" not in data


def _element(doc):
    return doc["fields"][1]["element"]


def _let(doc, **changes):
    return {**_element(doc)["owner"], **changes}


DAMAGE = {
    "missing_key": ("DOCUMENT", lambda d: d["fields"][1].pop("provenance")),
    "extra_key": ("DOCUMENT", lambda d: d["fields"][1].update(extra=None)),
    "kind": ("TAG", lambda d: d["fields"][1].update(kind="list")),
    "container_canonical": (
        "DOCUMENT",
        lambda d: d["fields"][1].update(canonical=d["fields"][0]["canonical"]),
    ),
    "container_declared": ("DOCUMENT", lambda d: d["fields"][1].update(declared=None)),
    "container_meaning": ("DOCUMENT", lambda d: d["fields"][1].update(meaning=0)),
    "container_role": ("DOCUMENT", lambda d: d["fields"][1].update(role="group_key")),
    "element_multiplicity": (
        "DOCUMENT",
        lambda d: _element(d).update(multiplicity="set"),
    ),
    "element_nullability": (
        "DOCUMENT",
        lambda d: _element(d).update(nullability="nullable"),
    ),
    "ordering_null": ("DOCUMENT", lambda d: _element(d).update(ordering=None)),
    "ordering_owner": (
        "DOCUMENT",
        lambda d: _element(d)["ordering"].update(owner=_let(d, let_position=1)),
    ),
    "let_position_missing": (
        "DOCUMENT",
        lambda d: _element(d)["owner"].pop("let_position"),
    ),
    "let_position_null": (
        "INDEX",
        lambda d: _element(d)["owner"].update(let_position=None),
    ),
    "let_position_negative": (
        "NUMBER",
        lambda d: _element(d)["owner"].update(let_position=-1),
    ),
    "let_not_query": (
        "DOCUMENT",
        lambda d: _element(d)["owner"]["identity"].update(kind="table"),
    ),
    "element_output_owner": (
        "DOCUMENT",
        lambda d: _element(d)["output"].update(owner=_let(d, let_position=1)),
    ),
    "child_nested": (
        "DOCUMENT",
        lambda d: _element(d)["fields"].__setitem__(
            0, {**deepcopy(d["fields"][1]), "ordinal": 0}
        ),
    ),
    "child_owner": (
        "REFERENCE",
        lambda d: _element(d)["fields"][0]["identity"].update(
            owner=_let(d, let_position=1)
        ),
    ),
    "child_output": (
        "REFERENCE",
        lambda d: _element(d)["fields"][0]["output"].update(position=99),
    ),
    "field_count": ("DOCUMENT", lambda d: _element(d).update(field_count=5)),
    "empty_element": (
        "DOCUMENT",
        lambda d: (
            _element(d).update(field_count=0, fields=[]),
            _element(d)["output"].update(field_count=0),
        ),
    ),
    "export_collision": (
        "REFERENCE",
        lambda d: _element(d)["fields"][0]["port"]["coordinate"].update(position=0),
    ),
    "child_port_owner": (
        "REFERENCE",
        lambda d: _element(d)["fields"][1]["port"]["owner"].update(position=5),
    ),
    "child_port_owner_is_top": (
        "REFERENCE",
        lambda d: [
            child["port"].update(owner=d["fields"][0]["port"]["owner"])
            for child in _element(d)["fields"]
        ],
    ),
    "child_meaning_without_description": (
        "REFERENCE",
        lambda d: d.pop("scalar_meaning"),
    ),
    "child_description_without_meaning": (
        "REFERENCE",
        lambda d: _element(d)["fields"][3].pop("meaning"),
    ),
    "types_unreachable": (
        "REFERENCE",
        lambda d: d["types"].append(
            {
                **d["types"][0],
                "id": 2,
                "owner": {**d["types"][0]["owner"], "declaration_position": 9},
            }
        ),
    ),
    "types_out_of_order": (
        "REFERENCE",
        lambda d: [
            _element(d)["fields"][position]["type_resolution"]["aliases"][0].update(
                index=index
            )
            for position, index in ((1, 1), (5, 0))
        ],
    ),
}


@pytest.mark.parametrize("name", DAMAGE)
def test_closed_v2_rejects_each_damage_with_its_category(flat, name):
    category, damage = DAMAGE[name]
    doc = nested(flat)
    damage(doc)
    with pytest.raises(pure.ContractDocumentError) as caught:
        pure.encode_document(doc)
    assert caught.value.category == category


OTHER = {**LET, "let_position": 1}


def _again(flat, let=None):
    """Collect a second time: the same let repeats its element record; another
    let brings its own definition, output, order and export coordinates."""
    doc = nested(flat)
    second = deepcopy(doc["fields"][1])
    second.update(ordinal=2, position=2, label="again")
    second["identity"].update(position=2, name="again")
    second["port"]["coordinate"]["position"] = 2
    element = second["element"]
    if let is not None:
        element["owner"] = element["ordering"]["owner"] = let
        element["output"].update(owner=let, position=50, producer=51)
        for key in element["ordering"]["keys"]:
            key["prepared"]["order"]["position"] = 1
        for child in element["fields"]:
            child["output"] = element["output"]
            child["identity"]["owner"] = let
            child["port"]["owner"]["position"] = 2
            child["port"]["coordinate"]["position"] += 100
    doc["fields"].append(second)
    doc["field_count"] = 3
    for holder in (doc, *doc["fields"]):
        holder["output"]["field_count"] = 3
    return json.loads(json.dumps(doc))


CROSS = {
    "same_let_twice": (None, None, None),
    "another_let": (None, OTHER, None),
    "same_let_other_output": (
        "REFERENCE",
        None,
        lambda e: [x["output"].update(position=77) for x in (e, *e["fields"])],
    ),
    "same_let_other_definition": (
        "REFERENCE",
        None,
        lambda e: [x["port"]["owner"].update(position=3) for x in e["fields"]],
    ),
    "same_let_false_for_zero": (
        "REFERENCE",
        None,
        lambda e: e["fields"][0]["identity"].update(position=False),
    ),
    "another_let_same_definition": (
        "REFERENCE",
        OTHER,
        lambda e: [x["port"]["owner"].update(position=0) for x in e["fields"]],
    ),
    "another_let_same_output": (
        "REFERENCE",
        OTHER,
        lambda e: [x["output"].update(position=40) for x in (e, *e["fields"])],
    ),
    "another_let_same_order": (
        "REFERENCE",
        OTHER,
        lambda e: [
            k["prepared"]["order"].update(position=0) for k in e["ordering"]["keys"]
        ],
    ),
    "another_let_same_exports": (
        "REFERENCE",
        OTHER,
        lambda e: [
            x["port"]["coordinate"].update(
                position=x["port"]["coordinate"]["position"] - 100
            )
            for x in e["fields"]
        ],
    ),
}


@pytest.mark.parametrize("name", CROSS)
def test_each_relation_owns_its_coordinates_across_collections(flat, name):
    """One let has one element record, and a definition, relation output or
    relation order belongs to one relation; no winner is chosen between two."""
    category, let, change = CROSS[name]
    doc = _again(flat, let)
    if change is not None:
        change(doc["fields"][2]["element"])
    if category is None:
        data = pure.encode_document(doc)
        assert pure.reencode_contract(pure.decode_contract(data)) == data
        same = doc["fields"][1]["element"] == doc["fields"][2]["element"]
        assert same is (let is None)
        return
    with pytest.raises(pure.ContractDocumentError) as caught:
        pure.encode_document(doc)
    assert caught.value.category == category


def test_a_repeated_element_is_judged_by_content_not_aliasing(flat):
    doc = _again(flat)
    data = pure.encode_document(doc)
    doc["fields"][2]["element"] = doc["fields"][1]["element"]
    pure.validate_document(doc)
    assert pure.encode_document(doc) == data


def _top_ordering(flat, order):
    """The flat root's own ordering beside the element's, at relation order `order`."""
    ordering = deepcopy(flat["ordering"])
    for key in ordering["keys"]:
        prepared = key["prepared"]
        prepared["order"]["position"] = order
        for name in ("item", "expression", "value"):
            prepared[name]["position"] += 2 * order
    return ordering


def test_a_relation_order_belongs_to_one_relation(flat):
    doc = {**nested(flat), "ordering": _top_ordering(flat, 1)}
    pure.decode_contract(pure.encode_document(doc))
    doc["ordering"] = _top_ordering(flat, 0)
    with pytest.raises(pure.ContractDocumentError, match="REFERENCE"):
        pure.encode_document(doc)


def test_one_format_per_meaning(flat):
    renamed = {**deepcopy(flat), "format": pure.FORMAT_V2}
    with pytest.raises(pure.ContractDocumentError, match="VERSION"):
        pure.encode_document(renamed)
    old = {**nested(flat), "format": pure.FORMAT}
    with pytest.raises(pure.ContractDocumentError, match="DOCUMENT"):
        pure.encode_document(old)
    pure.encode_document(flat)


def test_leaf_budget_counts_top_level_and_child_leaves(flat):
    doc = nested(flat)
    data = pure.encode_document(doc)
    for total in (2, 7):
        small = pure.DocumentLimits(fields=total)
        with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
            pure.encode_document(doc, limits=small)
        with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
            pure.decode_contract(data, limits=small)
    pure.decode_contract(data, limits=pure.DocumentLimits(fields=8))
    # A repeated element still carries, so counts, its child leaves.
    twice = pure.encode_document(_again(flat))
    with pytest.raises(pure.ContractDocumentError, match="LIMIT"):
        pure.decode_contract(twice, limits=pure.DocumentLimits(fields=14))
    pure.decode_contract(twice, limits=pure.DocumentLimits(fields=15))


def _swap_children(d):
    children = _element(d)["fields"]
    children[0], children[2] = children[2], children[0]
    for position, child in enumerate(children):
        child.update(ordinal=position, position=position)
        child["identity"]["position"] = position


def _rename_child(d):
    child = _element(d)["fields"][1]
    child["label"] = child["identity"]["name"] = "remark"


def _ascending(d):
    _element(d)["ordering"]["keys"][0].update(authored_direction="asc", direction="asc")


def _swap_meaning(d):
    children = _element(d)["fields"]
    children[3]["meaning"], children[4]["meaning"] = 1, 0


VARIANTS = {
    "child_order": _swap_children,
    "child_nullability": lambda d: _element(d)["fields"][0].update(
        nullability="nullable"
    ),
    "container_nullability": lambda d: d["fields"][1].update(nullability="nullable"),
    "child_declared_argument": lambda d: _element(d)["fields"][2]["declared"][
        "arguments"
    ][0]["value"].update(value="19"),
    "element_direction": _ascending,
    "hidden_key": lambda d: _element(d)["ordering"]["keys"][0]["expression"].update(
        name="note"
    ),
    "child_label": _rename_child,
    "child_meaning": _swap_meaning,
}


def test_source_digest_covers_every_nested_fact(flat):
    """Each single change is a different valid document, so a different digest."""
    documents = {
        "base": nested(flat),
        "let_position": nested(flat, {**LET, "let_position": 1}),
        "element_owner_name": nested(
            flat, {**LET, "identity": {**LET["identity"], "name": "older"}}
        ),
    }
    for name, change in VARIANTS.items():
        documents[name] = nested(flat)
        change(documents[name])
    digests = {
        name: hashlib.sha256(pure.encode_document(doc)).hexdigest()
        for name, doc in documents.items()
    }
    assert len(set(digests.values())) == len(digests) == 11


def test_scalar_kinds_are_an_allowlist(tmp_path, monkeypatch):
    assert c._SCALAR_KINDS == {
        ProjectResolvedTypeKind.BUILTIN,
        ProjectResolvedTypeKind.TYPE_ALIAS,
        ProjectResolvedTypeKind.ENUM,
    }
    checked = probe.build_neutral(
        tmp_path / "flat", {"main.pietto": probe.source("postgres")}
    )
    contract = c.build_result_contract(checked)
    monkeypatch.setattr(c, "_SCALAR_KINDS", frozenset((ProjectResolvedTypeKind.ENUM,)))
    with pytest.raises(c.ResultError, match="SCALAR_UNAVAILABLE"):
        c.build_result_contract(checked)
    with pytest.raises(c.ResultError, match="FIELD"):
        c.verify_result_contract(contract, checked)


def test_nested_shape_type_is_private():
    import pietto

    assert [f.name for f in fields(c.NestedShape)] == [
        "collect",
        "owner",
        "output",
        "multiplicity",
        "ordering",
        "fields",
    ]
    shape = c.NestedShape(None, None, None, None, None, ())
    with pytest.raises(FrozenInstanceError):
        setattr(shape, "owner", None)
    assert not hasattr(shape, "__dict__")
    assert shape != c.NestedShape(None, None, None, None, None, ())
    assert c.ResultField.__annotations__["shape"] == "ScalarShape | NestedShape"
    assert c.__all__ == () and pure.__all__ == ()
    assert not any(hasattr(pietto, n) for n in ("NestedShape", "scalar_fields"))


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("nested-readers")
    result = {}
    for target in ("postgres", "mysql"):
        checked, artifact = probe.build_source(root / target, target)
        contract = c.build_result_contract(checked)
        producer = p.bind_producer(contract, artifact, probe.observations(target))
        result[target] = (
            checked,
            artifact,
            contract,
            producer,
            o.prepare_output(artifact),
        )
    return result


def _nested_contract(contract):
    first, second = contract.shape.fields
    shape = c.NestedShape(
        None,
        contract.owner,
        contract.output,
        contract.multiplicity,
        contract.ordering,
        (first,),
    )
    return replace(contract, shape=c.ResultShape((first, replace(second, shape=shape))))


def _entries(target, roots):
    checked, artifact, contract, producer, output = roots[target]
    bad = _nested_contract(contract)
    view = writer.export_result_contract(contract, checked).view
    return bad, {
        "verify_output": lambda: o.verify_output(
            replace(output, contract=bad), artifact, bad
        ),
        # The shared binding check that execution requests run before connecting.
        "producer_columns": lambda: p._columns(bad, artifact),
        "bind_producer": lambda: p.bind_producer(
            bad, artifact, probe.observations(target)
        ),
        "verify_producer_binding": lambda: p.verify_producer_binding(
            replace(producer, contract=bad), bad, artifact
        ),
        "export_result_contract": lambda: writer.export_result_contract(bad, checked),
        "contract_digest": lambda: ipc.contract_digest(bad),
        "verify_contract_correspondence": lambda: (
            runtime.verify_contract_correspondence(view, bad, checked)
        ),
    }


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_flat_readers_refuse_a_nested_contract_as_a_result_error(roots, target):
    checked, artifact, contract, producer, output = roots[target]
    assert c.scalar_fields(contract) is contract.shape.fields
    bad, entries = _entries(target, roots)
    with pytest.raises(c.ResultError, match="NESTED_UNAVAILABLE"):
        c.scalar_fields(bad)
    for name, call in entries.items():
        with pytest.raises(c.ResultError) as caught:
            call()
        assert caught.value.category == "FIELD", name


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_flat_readers_refuse_explicitly_behind_an_admitting_authority(
    roots, target, monkeypatch
):
    """When an upstream authority admits nested shapes, each reader that is
    still flat refuses at its join point instead of misreading a leaf; the
    output view (open since S10) refuses a nested leaf that has no Collect
    column by correspondence."""
    artifact = roots[target][1]
    bad, entries = _entries(target, roots)
    monkeypatch.setattr(o, "verify_result_contract", lambda *args: None)
    monkeypatch.setattr(o, "build_result_contract", lambda *args, **kwargs: bad)
    monkeypatch.setattr(p, "verify_result_contract", lambda *args: None)
    entries["prepare_output"] = lambda: o.prepare_output(artifact)
    # A saved job's row layout reads its output's contract directly.
    output = roots[target][4]
    entries["layout"] = lambda: delivery.layout(replace(output, contract=bad), None)
    for name in ("producer_columns", "bind_producer", "verify_producer_binding"):
        with pytest.raises(c.ResultError, match="NESTED_UNAVAILABLE"):
            entries[name]()
    with pytest.raises(c.ResultError, match="NESTED_UNAVAILABLE"):
        entries["layout"]()
    for name in ("prepare_output", "verify_output"):
        with pytest.raises(c.ResultError, match="^OUTPUT_COLUMNS$"):
            entries[name]()


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    template, _ = compiled_template(
        tmp_path_factory.mktemp("nested-compiled") / "small", entry="bundle"
    )
    return c.build_result_contract(template.artifact.request.verification)


def _compiled_digest(contract, fields, version):
    """The compiled contract identity recomputed from its written rule."""
    document = {
        "fields": fields,
        "format": "pietto.compiled-result-contract." + version,
        "multiplicity": ["bag"],
        "pin": contract.authority.completed.root.expected_pin,
        "query": {"ref": ["entry", 0]},
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("ascii")).digest()


def test_compiled_digest_names_a_collection_by_the_v2_document(compiled, monkeypatch):
    """Behind an admitting authority the compiled digest of a nested contract
    is the v2 document of its leaves; a flat contract keeps its v1 bytes."""
    assert type(compiled.authority) is CompiledSQLPlanVerification
    renamed = [0, "renamed", "builtin", "Int", "non_null", None]
    other = [1, "other", "builtin", "Int", "nullable", None]
    assert ipc.contract_digest(compiled) == _compiled_digest(
        compiled, [renamed, other], "v1"
    )
    bad = _nested_contract(compiled)
    with pytest.raises(c.ResultError, match="FIELD"):
        ipc.contract_digest(bad)
    # The compiled branch reads its verifier from the contract module per call.
    monkeypatch.setattr(c, "verify_result_contract", lambda *args: None)
    collection = [1, "other", "collection", "nullable", [renamed]]
    assert ipc.contract_digest(bad) == _compiled_digest(
        compiled, [renamed, collection], "v2"
    )
    first, second = compiled.shape.fields
    nested = bad.shape.fields[1]

    def changed(*children, **container):
        shape = replace(nested.shape, fields=children)
        field = replace(nested, shape=shape, **container)
        return replace(bad, shape=c.ResultShape((first, field)))

    text = c.ScalarShape(
        first.shape.declared, replace(first.shape.canonical, name="Text")
    )
    variants = (
        changed(first),
        changed(replace(first, label="relabelled")),
        changed(replace(first, nullability=second.nullability)),
        changed(replace(first, shape=text)),
        changed(first, nullability=first.nullability),
        changed(first, second),
        changed(second, first),
    )
    digests = {ipc.contract_digest(variant) for variant in variants}
    assert len(digests) == len(variants)
    with pytest.raises(c.ResultError, match="FIELD"):
        ipc.contract_digest(changed(nested))


def test_a_real_compiled_collection_digest_is_its_v2_document(tmp_path):
    """S09 opens the compiled authority to a real nested contract: a real
    bundle's digest is the v2 document of its leaves, with no verifier
    replaced, on the root it was built on and on the root loaded from it."""
    import _pietto_sql_nested_collect as collecting
    from _pietto_plan_nested import sources
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    document = json.loads(collecting.contract())
    document["sources"] = document["sources"][:1]
    artifact = collecting.wired_outcome(
        tmp_path / "closed", sources("closed"), json.dumps(document)
    ).artifact
    assert artifact is not None
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    leaf = [0, "id", "builtin", "Int", "non_null", None]
    other = [1, "other", "builtin", "Int", "nullable", None]
    for root in (built.root, loaded):
        contract = c.build_result_contract(emit_compiled(root, ()).request.verification)
        assert type(contract.authority) is CompiledSQLPlanVerification
        assert ipc.contract_digest(contract) == _compiled_digest(
            contract,
            [leaf, [1, "nested", "collection", "non_null", [leaf, other]]],
            "v2",
        )


def test_flat_correspondence_refuses_a_v2_document_by_its_format(base, flat):
    """The document matches the flat root up to its last leaf, a collection; the
    refusal is the explicit format comparison, not a missing scalar key."""
    checked, contract = base
    doc = deepcopy(flat)
    last = doc["fields"][-1]
    collection = nested(flat)["fields"][1]
    for key in ("ordinal", "label", "identity", "port", "output", "position"):
        collection[key] = last[key]
    doc["fields"][-1] = collection
    doc.update(format=pure.FORMAT_V2, ordering=None)
    view = pure.decode_contract(pure.encode_document(doc))
    with pytest.raises(c.ResultError, match="CORRESPONDENCE") as caught:
        runtime.verify_contract_correspondence(view, contract, checked)
    assert caught.value.__cause__ is None


# A captured Top-K let with a hidden order key and every child kind the
# contract carries, and a closed let collected twice.
NESTED = """type Code = Text
shape Row:
    id: Int
    created: Int
    note: Text | None
    amount: Decimal(18, 4)
    stamp: Timestamp
    code: Code
source rows: Row = postgres.table("rows")
source others: Row = postgres.table("others")
query result:
    let recent:
        capture rows
        from others
        where others.id == rows.id
        select:
            note
            amount
            stamp
            code
        order by created desc, id
        limit 3
    let ids:
        from others
        select id
        order by id
    from rows
    select:
        id
        recent_rows = collect recent
        all_ids = collect ids
        again = collect ids
"""


def _producer(checked, name):
    (definition,) = (
        d
        for d in checked.plan.bindings.definitions
        if d.entry.owner.let_position is not None
        and d.entry.owner.identity.declared_name == name
    )
    return definition


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    checked = probe.build_neutral(
        tmp_path_factory.mktemp("nested-real") / "real", {"main.pietto": NESTED}
    )
    meaning = acquire_scalar_meaning(checked)
    return checked, c.build_result_contract(checked, scalar_meaning=meaning)


def test_build_binds_each_collection_to_its_upstream_authority(real):
    from pietto._project.project_sql_plan_nested import collect_of

    checked, contract = real
    plan = checked.plan
    top, recent, ids, again = contract.shape.fields
    assert type(top.shape) is c.ScalarShape
    assert [f.label for f in contract.shape.fields] == [
        "id",
        "recent_rows",
        "all_ids",
        "again",
    ]
    for leaf, name in ((recent, "recent"), (ids, "ids"), (again, "ids")):
        definition = _producer(checked, name)
        entry, shape = definition.entry, leaf.shape
        assert type(shape) is c.NestedShape and leaf.meaning is None
        assert leaf.port is plan.exports[leaf.ordinal]
        assert leaf.nullability is leaf.port.field.effective_nullability
        assert leaf.provenance is leaf.port.field.evidence.provenance
        assert shape.collect is collect_of(plan, leaf.port.ref)
        assert shape.collect in plan.collects
        assert shape.owner is entry.owner
        assert shape.output is entry.active_output
        assert shape.multiplicity is entry.active_properties.multiplicity
        assert shape.ordering is entry.active_properties.ordering
        assert [f.port for f in shape.fields] == list(definition.exports)
        for position, child in enumerate(shape.fields):
            evidence = child.port.field.evidence
            assert type(child.shape) is c.ScalarShape
            assert child.ordinal == position
            assert child.shape.canonical is evidence.resolved_type
            assert child.nullability is child.port.field.effective_nullability
    assert ids.shape.collect is not again.shape.collect
    assert ids.shape.owner is again.shape.owner
    # The hidden key `created` orders the element but is no child field.
    assert [f.label for f in recent.shape.fields] == ["note", "amount", "stamp", "code"]
    assert [f.label for f in ids.shape.fields] == ["id"]
    assert recent.shape.fields[2].meaning is contract.scalar_meaning.entries[1]
    assert [f.meaning for f in ids.shape.fields] == [None]
    with pytest.raises(c.ResultError, match="NESTED_UNAVAILABLE"):
        c.scalar_fields(contract)


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def test_writer_projects_v2_and_the_independent_checker_agrees(real):
    checked, contract = real
    export = writer.export_result_contract(contract, checked)
    runtime.verify_bound_export(export, checked)
    doc = export.view.document
    assert doc["format"] == "pietto.result-contract.v2"
    assert [f.get("kind") for f in doc["fields"]] == [
        None,
        "collection",
        "collection",
        "collection",
    ]
    recent, ids, again = (f["element"] for f in doc["fields"][1:])
    assert ids == again
    assert recent["owner"] == {
        "identity": {
            "module": "main.pietto",
            "namespace": "relation",
            "kind": "query",
            "name": "recent",
        },
        "module_position": 0,
        "declaration_position": 4,
        "let_position": 0,
    }
    assert ids["owner"]["let_position"] == 1
    assert (recent["multiplicity"], recent["nullability"]) == ("bag", "non_null")
    assert [
        (f["label"], f["canonical"]["name"], f["nullability"], f.get("meaning"))
        for f in recent["fields"]
    ] == [
        ("note", "Text", "nullable", None),
        ("amount", "Decimal", "non_null", None),
        ("stamp", "Timestamp", "non_null", 1),
        ("code", "Text", "non_null", None),
    ]
    assert [
        a["value"]["value"] for a in recent["fields"][1]["declared"]["arguments"]
    ] == [
        "18",
        "4",
    ]
    assert recent["fields"][3]["declared"]["name"] == "Code"
    assert [t["owner"]["identity"]["name"] for t in doc["types"]] == ["Code"]
    assert [
        (k["expression"]["name"], k["direction"]) for k in recent["ordering"]["keys"]
    ] == [("created", "desc"), ("id", "asc")]
    assert [f["nullability"] for f in doc["fields"][1:]] == ["non_null"] * 3
    # The contract describes the result shape, not the query: no LIMIT.
    assert "limit" not in set(_keys(doc))
    assert b"nested_relation" not in export.canonical_bytes
    digest = ipc.contract_digest(contract)
    assert digest == hashlib.sha256(export.canonical_bytes).digest()


def test_source_digest_is_stable_and_covers_the_element(tmp_path):
    def digest(name, text):
        checked = probe.build_neutral(tmp_path / name, {"main.pietto": text})
        return ipc.contract_digest(c.build_result_contract(checked))

    base = digest("base", NESTED)
    assert digest("again", NESTED) == base
    # Only the child order key differs.
    assert (
        digest("key", NESTED.replace("order by created desc, id", "order by id"))
        != base
    )
    # Only the collected let differs; its child schema is the same.
    renamed = NESTED.replace("let ids:", "let keys:").replace(
        "collect ids", "collect keys"
    )
    assert digest("let", renamed) != base


def test_a_collected_let_ordered_by_a_header_parameter_exports(tmp_path):
    # The element ordering shares the flat expression codec, parameter reads too.
    text = NESTED.replace("query result:", "query result(p: Int):").replace(
        "order by id\n", "order by id * p, id\n"
    )
    checked = probe.build_neutral(tmp_path / "parameter", {"main.pietto": text})
    contract = c.build_result_contract(
        checked, scalar_meaning=acquire_scalar_meaning(checked)
    )
    export = writer.export_result_contract(contract, checked)
    runtime.verify_bound_export(export, checked)
    assert pure.reencode_contract(export.view) == export.canonical_bytes
    element = export.view.document["fields"][2]["element"]
    read = element["ordering"]["keys"][0]["expression"]["right"]
    assert {k: v for k, v in read.items() if k != "location"} == {
        "tag": "parameter",
        "name": "p",
        "ordinal": 0,
        "type_name": "Int",
        "nullability": "not_null",
    }
    assert (
        ipc.contract_digest(contract) == hashlib.sha256(export.canonical_bytes).digest()
    )


@pytest.fixture(scope="module")
def foreign(tmp_path_factory):
    checked = probe.build_neutral(
        tmp_path_factory.mktemp("nested-foreign") / "foreign", {"main.pietto": NESTED}
    )
    return c.build_result_contract(
        checked, scalar_meaning=acquire_scalar_meaning(checked)
    )


def _damaged(contract, foreign):
    top, recent, ids, again = contract.shape.fields
    shape = recent.shape
    children = shape.fields

    def element(**changes):
        return {1: replace(recent, shape=replace(shape, **changes))}

    def child(position, **changes):
        fields = list(children)
        fields[position] = replace(fields[position], **changes)
        return element(fields=tuple(fields))

    first, second = children[0], children[1]
    return {
        "child_deleted": element(fields=children[:-1]),
        "child_duplicated": element(fields=(*children, children[0])),
        "children_swapped": element(fields=(second, first, *children[2:])),
        "children_swapped_renumbered": element(
            fields=(
                replace(second, ordinal=0),
                replace(first, ordinal=1),
                *children[2:],
            )
        ),
        "child_list": element(fields=list(children)),
        "element_owner": element(owner=ids.shape.owner),
        "element_output": element(output=ids.shape.output),
        "element_ordering": element(ordering=ids.shape.ordering),
        "element_ordering_none": element(ordering=None),
        # Equal to the retained BAG, but not that occurrence.
        "element_multiplicity": element(multiplicity="bag"),
        "element_collect": element(collect=ids.shape.collect),
        "repeated_collect": {3: replace(again, shape=ids.shape)},
        "container_nullability": {
            1: replace(recent, nullability=ProjectRowFieldNullability.NULLABLE)
        },
        "container_meaning": {1: replace(recent, meaning=children[2].meaning)},
        "foreign_child_port": child(
            0, port=foreign.shape.fields[1].shape.fields[0].port
        ),
        "foreign_element": {1: foreign.shape.fields[1]},
        "child_meaning": child(2, meaning=None),
        "child_nullability": child(0, nullability=ProjectRowFieldNullability.NON_NULL),
        "child_nested": child(0, shape=ids.shape),
        "nested_on_scalar_port": {0: replace(top, shape=shape)},
        "scalar_on_nested_port": {
            1: replace(
                recent,
                shape=c.ScalarShape(None, recent.port.field.evidence.resolved_type),
            )
        },
    }


@pytest.mark.parametrize(
    "name",
    (
        "child_deleted",
        "child_duplicated",
        "children_swapped",
        "children_swapped_renumbered",
        "child_list",
        "element_owner",
        "element_output",
        "element_ordering",
        "element_ordering_none",
        "element_multiplicity",
        "element_collect",
        "repeated_collect",
        "container_nullability",
        "container_meaning",
        "foreign_child_port",
        "foreign_element",
        "child_meaning",
        "child_nullability",
        "child_nested",
        "nested_on_scalar_port",
        "scalar_on_nested_port",
    ),
)
def test_verify_refuses_each_damaged_collection_as_field(real, foreign, name):
    checked, contract = real
    fields = list(contract.shape.fields)
    for position, leaf in _damaged(contract, foreign)[name].items():
        fields[position] = leaf
    bad = replace(contract, shape=c.ResultShape(tuple(fields)))
    with pytest.raises(c.ResultError) as caught:
        c.verify_result_contract(bad, checked)
    assert caught.value.category == "FIELD"


def test_build_refuses_a_broken_lineage_or_meaning(tmp_path, monkeypatch):
    from pietto._project import project_scalar_meaning as meaning
    from pietto._project import project_sql_plan_nested as nested

    checked = probe.build_neutral(tmp_path / "broken", {"main.pietto": NESTED})
    bundle = acquire_scalar_meaning(checked)
    original = meaning._output_entry

    def no_child_meaning(scalar_meaning, port):
        if port.field.evidence.resolved_type.name == "Timestamp":
            raise meaning.ScalarMeaningError("MEANING_OUTPUT")
        return original(scalar_meaning, port)

    monkeypatch.setattr(meaning, "_output_entry", no_child_meaning)
    with pytest.raises(c.ResultError, match="MEANING_UNAVAILABLE"):
        c.build_result_contract(checked, scalar_meaning=bundle)
    monkeypatch.setattr(meaning, "_output_entry", original)

    def no_lineage(plan, port):
        raise ValueError("Port carries no one Collect read.")

    monkeypatch.setattr(nested, "collect_of", no_lineage)
    with pytest.raises(c.ResultError, match="NESTED_ELEMENT"):
        c.build_result_contract(checked)


def _graft(checked, other):
    """Write `recent`'s element order from another, JOIN-read let; the schema
    alone cannot tell, as that relation order is claimed by no other relation."""
    ordering = _producer(checked, other).entry.active_properties.ordering
    original = writer._Projection.ordering

    def grafted(self, value, owner_record=None):
        if owner_record is None:
            return original(self, value)
        let = value.evidence.owner
        if let.identity.declared_name != "recent":
            return original(self, value, owner_record)
        return original(self, ordering, lambda _owner: owner_record(let))

    return grafted


WRITER_DAMAGE = ("children_swapped", "let_position", "ordering_graft")


@pytest.mark.parametrize("name", WRITER_DAMAGE)
def test_independent_checker_finds_each_writer_damage(tmp_path, monkeypatch, name):
    text = NESTED.replace(
        "    from rows\n    select:\n        id\n",
        "    let peer:\n        from others\n        select id\n        order by id desc\n"
        "    from rows\n    inner join peer on rows.id == peer.id\n"
        "    select:\n        id = rows.id\n",
    )
    checked = probe.build_neutral(tmp_path / name, {"main.pietto": text})
    contract = c.build_result_contract(checked)
    runtime.verify_bound_export(
        writer.export_result_contract(contract, checked), checked
    )
    if name == "children_swapped":
        original = writer._Projection.collection

        def swapped(self, leaf):
            described = original(self, leaf)
            children = described["element"]["fields"]
            if len(children) > 1:
                children[0], children[1] = children[1], children[0]
                for position, child in enumerate(children):
                    child.update(ordinal=position, position=position)
                    child["identity"]["position"] = position
            return described

        monkeypatch.setattr(writer._Projection, "collection", swapped)
    elif name == "let_position":
        original = writer._Projection.let_owner

        def shifted(self, value):
            described = original(self, value)
            described["let_position"] += 7
            return described

        monkeypatch.setattr(writer._Projection, "let_owner", shifted)
    else:
        monkeypatch.setattr(writer._Projection, "ordering", _graft(checked, "peer"))
    export = writer.export_result_contract(contract, checked)
    with pytest.raises(c.ResultError, match="CORRESPONDENCE"):
        runtime.verify_bound_export(export, checked)


# -- S10: the binding join point over real PostgreSQL Collect outputs ---------


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    """Real VERIFIED Collect outputs: a captured and a closed let, and a parent
    with its own ORDER BY and LIMIT (the result body carries the group)."""
    root = tmp_path_factory.mktemp("nested-binding")
    return {
        name: nested_helper.collected(probe, root / name, **options)
        for name, options in (
            ("captured", {}),
            ("closed", {"closed": True}),
            ("ordered", {"ordered": True}),
        )
    }


def _description(names_and_codes):
    return tuple(nested_helper.Column(n, t, None) for n, t in names_and_codes)


DESCRIPTION = (("renamed", 20), ("c", 20), ("i", 1016), ("b", 1000), ("t", 1009))


@pytest.mark.parametrize("name", ("captured", "closed", "ordered"))
def test_a_real_collect_output_binds_its_carrier_descriptor(outputs, name):
    arrow = "pyarrow" in sys.modules
    output = outputs[name]
    assert o.verify_output(output, output.artifact, output.contract) is output.columns
    flat, column = output.columns
    assert (type(flat), type(column)) == (o.OutputColumn, o.NestedOutputColumn)
    assert (column.ordinal, column.label, column.carrier, column.aliases) == (
        1,
        "c",
        "pg_column_arrays_v1",
        ("c", "i", "b", "t"),
    )
    leaf = output.contract.shape.fields[1]
    assert column.field is leaf and column.export is leaf.port
    assert [
        (child.ordinal, child.label, child.realization.storage, child.field)
        for child in column.children
    ] == [
        (k, label, {"kind": storage}, field)
        for k, (label, storage, field) in enumerate(
            zip(("i", "b", "t"), ("pg_int8", "pg_bool", "pg_text"), leaf.shape.fields)
        )
    ]
    for producer in (
        bind_postgres_output(output, _description(DESCRIPTION)),
        bind_stored_output(output, "postgres_rows"),
    ):
        p.verify_producer_binding(producer, output.contract, output.artifact)
        bound = producer.fields[1]
        assert type(bound) is p.ProducerNestedBinding
        assert (bound.field, bound.column, bound.nullable) == (leaf, column, False)
        assert bound.count == p.ProducerObservation(
            1, "c", "postgres", "pg_int8", 0, 1 << 20, domain="child_count"
        )
        assert [
            (
                b.field,
                b.column,
                b.nullable,
                b.observation.ordinal,
                b.observation.label,
                b.observation.storage,
                b.observation.carrier,
                b.observation.protocol_nullable,
            )
            for b in bound.children
        ] == [
            (
                leaf.shape.fields[0],
                column.children[0],
                False,
                0,
                "i",
                "pg_int8",
                "int",
                None,
            ),
            (
                leaf.shape.fields[1],
                column.children[1],
                True,
                1,
                "b",
                "pg_bool",
                "bool",
                None,
            ),
            (
                leaf.shape.fields[2],
                column.children[2],
                True,
                2,
                "t",
                "pg_text",
                "str",
                None,
            ),
        ]
        assert bound.children[0].observation.lower == -(2**63)
        assert bound.children[2].observation.text == p.TextObservation(
            256, "UTF8", "C", "NO PAD"
        )
    # Binding and decoding never import Arrow.
    assert ("pyarrow" in sys.modules) is arrow


def _swap(items, a, b):
    items = list(items)
    items[a], items[b] = items[b], items[a]
    return tuple(items)


DESCRIPTION_DAMAGE = {
    "count_oid": DESCRIPTION[:1] + (("c", 23),) + DESCRIPTION[2:],
    "int8_child_as_int4_array": DESCRIPTION[:2] + (("i", 1007),) + DESCRIPTION[3:],
    "children_swapped": DESCRIPTION[:2] + _swap(DESCRIPTION[2:], 0, 1),
    "array_missing": DESCRIPTION[:-1],
    "array_extra": DESCRIPTION + (("t", 1009),),
    "count_alias": DESCRIPTION[:1] + (("c_count", 20),) + DESCRIPTION[2:],
    "child_alias": DESCRIPTION[:4] + (("text", 1009),),
    "scalar_child_oid": DESCRIPTION[:3] + (("b", 16),) + DESCRIPTION[4:],
}


@pytest.mark.parametrize("damage", sorted(DESCRIPTION_DAMAGE))
def test_a_description_must_match_the_descriptor_by_position(outputs, damage):
    output = outputs["captured"]
    with pytest.raises(c.ResultError, match="^EXECUTION_METADATA$"):
        bind_postgres_output(output, _description(DESCRIPTION_DAMAGE[damage]))


def test_only_the_rows_carrier_reads_a_collected_field(outputs):
    output = outputs["captured"]
    description = _description(DESCRIPTION)
    # ADBC is refused by the binder after connecting (S12 refuses it before).
    with pytest.raises(c.ResultError, match="^NESTED_UNAVAILABLE$"):
        bind_native_output(output, "postgres_adbc", description)
    with pytest.raises(c.ResultError, match="^NESTED_UNAVAILABLE$"):
        decode_native_rows(output, "postgres_adbc", description, ())
    with pytest.raises(c.ResultError, match="^EXECUTION_METADATA_ROUTE$"):
        bind_native_output(output, "mysql_rows", description)


@pytest.mark.parametrize("key", ("Float", "Decimal", "Date", "Timestamp", "UUID"))
def test_an_unopened_child_leaf_is_refused_at_binding(tmp_path, key):
    output = nested_helper.collected(probe, tmp_path / key, (("x", key, True),))
    for bind in (
        lambda: bind_postgres_output(output, nested_helper.metadata(output)),
        lambda: bind_stored_output(output, "postgres_rows"),
    ):
        with pytest.raises(c.ResultError, match="^PRODUCER_UNSUPPORTED$"):
            bind()


def _replace_nested(producer, **changes):
    first, bound = producer.fields
    return replace(producer, fields=(first, replace(bound, **changes)))


def test_a_coordinated_binding_change_is_refused(outputs):
    output = outputs["captured"]
    producer = bind_postgres_output(output, _description(DESCRIPTION))
    bound = producer.fields[1]
    assert type(bound) is p.ProducerNestedBinding
    child = bound.children[0]
    damaged = {
        "count_upper": (
            {"count": replace(bound.count, upper=(1 << 20) - 1)},
            "PRODUCER_OBSERVATION",
        ),
        "count_bool": (
            {"count": replace(bound.count, lower=False)},
            "PRODUCER_OBSERVATION",
        ),
        "count_storage": (
            {"count": replace(bound.count, storage="pg_int4")},
            "PRODUCER_OBSERVATION",
        ),
        "container_nullable": ({"nullable": True}, "PRODUCER_OBSERVATION"),
        "child_range": (
            {
                "children": (
                    replace(child, observation=replace(child.observation, upper=5)),
                    *bound.children[1:],
                )
            },
            "PRODUCER_OBSERVATION",
        ),
        "child_nullable": (
            {"children": (replace(child, nullable=True), *bound.children[1:])},
            "PRODUCER_OBSERVATION",
        ),
        "children_swapped": (
            {"children": _swap(bound.children, 0, 1)},
            "PRODUCER_FIELDS",
        ),
        "child_dropped": ({"children": bound.children[:-1]}, "PRODUCER_FIELDS"),
        "child_repeated": (
            {"children": (child, child, bound.children[2])},
            "PRODUCER_FIELDS",
        ),
        "column": ({"column": output.columns[0]}, "PRODUCER_FIELDS"),
    }
    for name, (changes, category) in damaged.items():
        with pytest.raises(c.ResultError) as caught:
            p.verify_producer_binding(
                _replace_nested(producer, **changes), output.contract, output.artifact
            )
        assert caught.value.category == category, name
    flat = replace(producer, fields=(producer.fields[0], producer.fields[0]))
    with pytest.raises(c.ResultError, match="^PRODUCER_FIELDS$"):
        p.verify_producer_binding(flat, output.contract, output.artifact)


def test_a_damaged_carrier_descriptor_is_refused(outputs):
    output = outputs["captured"]
    flat, column = output.columns
    children = column.children
    damaged = {
        "carrier": (replace(column, carrier="pg_json_v1"), "OUTPUT_CARRIER"),
        "aliases": (replace(column, aliases=("c", "b", "i", "t")), "OUTPUT_CARRIER"),
        "alias_dropped": (replace(column, aliases=("c", "i", "b")), "OUTPUT_CARRIER"),
        "child_dropped": (replace(column, children=children[:-1]), "OUTPUT_CARRIER"),
        "children_swapped": (
            replace(column, children=_swap(children, 0, 1)),
            "OUTPUT_COLUMNS",
        ),
        "child_realization": (
            replace(
                column,
                children=(
                    replace(children[0], realization=children[1].realization),
                    *children[1:],
                ),
            ),
            "OUTPUT_REALIZATION",
        ),
        "child_terminal": (
            replace(
                column,
                children=(
                    replace(children[0], terminal=column.terminal),
                    *children[1:],
                ),
            ),
            "OUTPUT_COLUMNS",
        ),
        "as_scalar": (flat, "OUTPUT_COLUMNS"),
    }
    for name, (supplied, category) in damaged.items():
        with pytest.raises(c.ResultError) as caught:
            o.verify_output(
                replace(output, columns=(flat, supplied)),
                output.artifact,
                output.contract,
            )
        assert caught.value.category == category, name
    # Another real Collect's descriptor is not this statement's.
    other = outputs["closed"].columns[1]
    with pytest.raises(c.ResultError, match="^OUTPUT_COLUMNS$"):
        o.verify_output(
            replace(output, columns=(flat, other)), output.artifact, output.contract
        )


def test_every_still_flat_reader_refuses_a_real_collect_output(outputs):
    output = outputs["captured"]
    artifact, contract = output.artifact, output.contract
    request = SimpleNamespace(
        output=None, contract=contract, artifact=artifact, projection=None
    )
    access = PostgresAccess("127.0.0.1", 5432, "phase66", "pietto_query", "x")
    guarded = replace(output, guarded=object())
    entries = {
        # postgres_rows without an output, SQLSelect and native projections.
        "producer_columns": lambda: p._columns(contract, artifact),
        "bind_native_projection": lambda: bind_native_projection(
            request, _description(DESCRIPTION)
        ),
        "prepare_execution": lambda: prepare_execution(artifact, access),
        # A guarded program reads scalar leaves only (S12/S20).
        "guarded_output": lambda: o.verify_output(guarded, artifact, contract),
        "guarded_columns": lambda: p._columns(contract, artifact, None, guarded),
        # R2 and guard source closures (S12/S20).
        "source_read_columns": lambda: o.source_read_columns(output),
        # A saved job's row layout and IPC framing (S17).
        "layout": lambda: delivery.layout(output, None),
    }
    for name, call in entries.items():
        with pytest.raises(c.ResultError) as caught:
            call()
        assert caught.value.category == "NESTED_UNAVAILABLE", name
    # The opened route: a nested output request is checked before connecting.
    request = prepare_execution(artifact, access, output=output)
    assert request.output is output


def test_the_compiled_descriptor_equals_the_live_one(tmp_path):
    """S09 F-12: the compiled artifact's carrier descriptor is the live one's."""
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    live = nested_helper.collected(probe, tmp_path / "live")
    build = build_compiled(live.artifact)
    loaded = load_compiled(
        build.payload,
        expected_pin=build.pin,
        accepted_producer=build.producer,
        accepted_compatibility=build.compatibility,
    )
    compiled = emit_compiled(loaded, ())
    output = o.prepare_output(compiled)

    def descriptor(output):
        column = output.columns[1]
        return (
            column.carrier,
            column.aliases,
            [(child.label, child.realization.storage) for child in column.children],
        )

    assert descriptor(output) == descriptor(live)
    assert compiled.rendered.sql == live.artifact.rendered.sql
