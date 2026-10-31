"""Phase71 S10 nested Arrow mechanics; importing the checker layer needs no Arrow.

Nested producers are real: a VERIFIED PostgreSQL Collect (S08), its output's
``pg_column_arrays_v1`` descriptor and a psycopg-shaped description bound by the
rows reader (``real``). No real upstream yields a NULLABLE container before S16,
so only those parts replace exactly one name, ``project_arrow_result.
verify_producer_binding``, and record the category the real entry returns
without that seam; their parent shape is assembled over real flat child leaves.
"""

from collections import namedtuple
from contextlib import contextmanager
from dataclasses import replace
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, cast
from unittest.mock import patch

GROUPS = (
    "nested_arrow_type",
    "nested_binding_equality",
    "nested_owned_values",
    "nested_construction_refusals",
    "nested_accounting",
    "nested_verification",
    "nested_guards",
)
LOW, HIGH = -(2**63), 2**63 - 1
SMILE = "\U0001f600" * 3
ROWS = (
    (7, ((7, 7), (True, True), ("a", "a"))),
    (7, ((7, 7), (True, True), ("a", "a"))),
    (0, ((), (), ())),
    (1, ((5,), (None,), (None,))),
    (2, ((LOW, HIGH), (False, True), (SMILE, ""))),
)
NULLABLE_ROWS = ((1, None), (2, ((3,), (True,), ("x",))))
# pg_column_arrays_v1 rows as psycopg returns them (S02 invariant 2): renamed,
# then the count and one array per child. Duplicates; the empty collection (a
# zero count, NULL arrays); an all-NULL child row; Int64 limits, the empty and
# the 'NULL' string; array-quoting characters, a multibyte one and a tie.
QUOTED = ',{}"\\'
CARRIER_ROWS = (
    (7, 2, [7, 7], [True, True], ["a", "a"]),
    (0, 0, None, None, None),
    (1, 1, [5], [None], [None]),
    (2, 3, [LOW, HIGH, 0], [False, True, False], [SMILE, "", "NULL"]),
    (3, 2, [4, 4], [False, False], [QUOTED, "\u00e9"]),
)
TEXT = {
    "kind": "text",
    "max_characters": 256,
    "encoding": "UTF8",
    "collation": "C",
    "padding": "NO PAD",
}
# Source kind, storage and domain of each real donor leaf.
LEAVES = {
    "Int8": ("Int", "pg_int8", {"kind": "int_range", "min": LOW, "max": HIGH}),
    "Int4": (
        "Int",
        "pg_int4",
        {"kind": "int_range", "min": -(2**31), "max": 2**31 - 1},
    ),
    "Int2": (
        "Int",
        "pg_int2",
        {"kind": "int_range", "min": -(2**15), "max": 2**15 - 1},
    ),
    "Bool": ("Bool", "pg_bool", {"kind": "bool01"}),
    "Text": ("Text", "pg_text", TEXT),
}
# Real children the rows reader does not open yet (S14/S15): authored type,
# storage and domain. A Date child is derived: date_of(<label>_at).
UNOPENED = {
    "Float": (
        "Float",
        {"kind": "pg_float8"},
        {"kind": "finite_float", "format": "binary64"},
    ),
    "Decimal": (
        "Decimal(9, 2)",
        {"kind": "pg_numeric", "precision": 9, "scale": 2},
        {"kind": "decimal", "precision": 9, "scale": 2},
    ),
    "Timestamp": (
        "Timestamp",
        {"kind": "pg_timestamp", "fractional_seconds": 6},
        {"kind": "timestamp"},
    ),
    "UUID": (
        "UUID",
        {"kind": "pg_uuid"},
        {"kind": "uuid", "encoding": "standard_bytes"},
    ),
}
IBT = (("i", "Int8", False), ("b", "Bool", True), ("t", "Text", True))
# PostgreSQL type OIDs, by storage: the int8 count and each child's array.
COUNT_OID = 20
ARRAY_OIDS = {"pg_int8": 1016, "pg_int4": 1007, "pg_int2": 1005, "pg_bool": 1000}
ARRAY_OIDS["pg_text"] = 1009
Column = namedtuple("Column", "name type_code null_ok")
ALLOCATORS = frozenset(
    ("array", "Array", "StructArray", "ListArray", "RecordBatch", "py_buffer")
)


def outcome(action):
    """A private category, ACCEPTED, or the raw exception type (never expected)."""
    from pietto._project.project_result_contract import ResultError

    try:
        action()
    except ResultError as exc:
        return exc.category
    except Exception as exc:
        return "raw:" + type(exc).__name__
    return "ACCEPTED"


@contextmanager
def admitted():
    """The one S10-A seam (AC-11): stands in for the S07-B/S08 nested authority."""
    from pietto._project import project_arrow_result as a

    with patch.object(a, "verify_producer_binding", lambda *args: None):
        yield


def donor(p, directory, leaves):
    """Real verified flat leaves of a PostgreSQL source: (contract, producer)."""
    from pietto._project.project_result_binding import (
        ProducerObservation,
        TextObservation,
        bind_producer,
    )
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_sql_emission import emit_project_sql

    text = "shape Row:\n" + "".join(
        f"    {label}: {LEAVES[key][0]}{' | None' if nullable else ''}\n"
        for label, key, nullable in leaves
    )
    text += 'source rows: Row = postgres.table("opaque.result.fixture")\n'
    text += "table result:\n    from rows\n    select:\n"
    text += "".join(f"        {label}\n" for label, _, _ in leaves)
    checked = p.build_neutral(directory, {"main.pietto": text})
    document = json.loads(p.emission_input("postgres"))
    fields, observed = [], []
    for i, (label, key, nullable) in enumerate(leaves):
        kind, storage, domain = LEAVES[key]
        if kind == "Int":
            domain = {**domain, "min": str(domain["min"]), "max": str(domain["max"])}
        fields.append(
            dict(
                ordinal=i,
                name=label,
                column=label,
                representation=dict(
                    storage={"kind": storage}, nullable=nullable, domain=domain
                ),
            )
        )
        observed.append(
            ProducerObservation(
                i,
                label,
                "postgres",
                storage,
                int(domain["min"]) if kind == "Int" else None,
                int(domain["max"]) if kind == "Int" else None,
                domain=domain["kind"],
                carrier={"Int": "int", "Bool": "bool", "Text": "str"}[kind],
                text=TextObservation(256, "UTF8", "C", "NO PAD")
                if kind == "Text"
                else None,
            )
        )
    document["sources"][0]["fields"] = fields
    result = emit_project_sql(checked, json.dumps(document).encode())
    assert result.status == "VERIFIED" and result.artifact is not None
    contract = build_result_contract(checked)
    return contract, bind_producer(contract, result.artifact, tuple(observed))


def collected(
    p,
    directory,
    children=IBT,
    *,
    alone=False,
    closed=False,
    ordered=False,
    where=None,
    kid_where=None,
):
    """A real VERIFIED PostgreSQL Collect and its output: `rows` (`renamed`,
    unless ``alone``) collecting `members`, the `kids` of each row (or every
    kid when ``closed``) in `seq` order; ``ordered`` adds the parent's own
    ORDER BY and LIMIT, so the result body carries the group. ``where``
    filters the parent rows and ``kid_where`` a captured row's kids."""
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning
    from pietto._project.project_sql_emission import emit_project_sql

    # The kid column each child reads: a Date child derives from a Timestamp.
    columns = tuple(
        (f"{label}_at", "Timestamp", nullable)
        if key == "Date"
        else (label, key, nullable)
        for label, key, nullable in children
    )
    text = "shape Kid:\n    parent: Int\n    seq: Int\n" + "".join(
        f"    {name}: {(LEAVES.get(key) or UNOPENED[key])[0]}"
        f"{' | None' if nullable else ''}\n"
        for name, key, nullable in columns
    )
    text += (
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("opaque.result.fixture")\n'
        'source kids: Kid = postgres.table("opaque.result.kids")\n'
        "query result:\n    let members:\n"
        + ("" if closed else "        capture rows\n")
        + "        from kids\n"
        + (
            ""
            if closed
            else "        where kids.parent == rows.id"
            + (f" and {kid_where}" if kid_where else "")
            + "\n"
        )
        + "        select:\n"
        + "".join(
            f"            {label} = date_of({label}_at)\n"
            if key == "Date"
            else f"            {label}\n"
            for label, key, _ in children
        )
        + "        order by:\n            seq\n"
        + "    from rows\n"
        + (f"    where {where}\n" if where else "")
        + "    select:\n"
        + ("" if alone else "        renamed = id\n")
        + "        c = collect members\n"
        + ("    order by:\n        rows.id desc\n    limit 4\n" if ordered else "")
    )
    checked = p.build_neutral(directory, {"main.pietto": text})
    document = json.loads(p.emission_input("postgres"))
    rows = document["sources"][0]
    rows["fields"] = rows["fields"][:1]
    rows["fields"][0]["representation"]["nullable"] = False
    kids = json.loads(json.dumps(rows))
    kids["selector"]["name"] = kids["relation"]["name"] = "kids"

    def field(ordinal, name, key, nullable):
        if key in LEAVES:
            _, storage, domain = LEAVES[key]
            storage = {"kind": storage}
            if domain["kind"] == "int_range":
                domain = {
                    **domain,
                    "min": str(domain["min"]),
                    "max": str(domain["max"]),
                }
        else:
            _, storage, domain = UNOPENED[key]
        return dict(
            ordinal=ordinal,
            name=name,
            column=name,
            representation=dict(storage=storage, nullable=nullable, domain=domain),
        )

    kids["fields"] = [
        field(0, "parent", "Int8", False),
        field(1, "seq", "Int8", False),
        *(field(2 + k, *column) for k, column in enumerate(columns)),
    ]
    document["sources"].append(kids)
    document["environment"].append(
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
    )
    outcome = emit_project_sql(
        checked,
        json.dumps(document).encode(),
        scalar_meaning=acquire_scalar_meaning(checked),
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    return prepare_output(outcome.artifact)


def metadata(output):
    """A psycopg-shaped description of the statement: the hand OID tables,
    each physical column under its own alias."""
    from pietto._project.project_result_output import NestedOutputColumn

    result = []
    for column in output.columns:
        if type(column) is not NestedOutputColumn:
            assert column.realization.storage == {"kind": "pg_int8"}
            result.append(Column(column.label, COUNT_OID, None))
            continue
        result.append(Column(column.aliases[0], COUNT_OID, None))
        result.extend(
            Column(alias, ARRAY_OIDS.get(child.realization.storage["kind"], 0), None)
            for alias, child in zip(column.aliases[1:], column.children, strict=True)
        )
    return tuple(result)


def real(p, directory, children=IBT, **options):
    """The rows reader's real binding of a real Collect output (S10-B)."""
    from pietto._project.project_execution_reader import bind_postgres_output

    output = collected(p, directory, children, **options)
    return bind_postgres_output(output, metadata(output))


def fixtures(p, root, *, light=False):
    from pietto._project.project_result_binding import bind_producer
    from pietto._project.project_result_contract import build_result_contract

    root.mkdir(parents=True, exist_ok=True)
    checked, artifact = p.build_source(root / "parent", "postgres")
    contract = build_result_contract(checked)
    parent = (
        contract,
        artifact,
        bind_producer(contract, artifact, p.observations("postgres")),
    )
    ibt = (("i", "Int8", False), ("b", "Bool", True), ("t", "Text", True))
    result: dict[str, Any] = {
        "parent": parent,
        "ibt": donor(p, root / "ibt", ibt)[1].fields,
    }
    if light:
        return result
    result["text"] = donor(p, root / "text", (("t", "Text", True),))[1].fields
    result["wide"] = donor(
        p, root / "wide", tuple((f"c{k}", "Int8", False) for k in range(64))
    )[1].fields
    return result


def real_fixtures(p, root):
    """Real producers (S08 output, S10 rows binding) of each S10 shape, and
    the bind-time category of each child leaf the reader does not open yet."""
    root.mkdir(parents=True, exist_ok=True)
    wide = tuple((f"c{k}", "Int8", False) for k in range(64))
    shapes = {
        "ibt": (IBT, {}),
        "closed": (IBT, {"closed": True}),
        "ordered": (IBT, {"ordered": True}),
        "widths": ((("w4", "Int4", False), ("w2", "Int2", True)), {}),
        "text": ((("t", "Text", True),), {"alone": True}),
        "wide": (wide[:63], {"alone": True}),
        "wider": (wide, {"alone": True}),
    }
    result: dict[str, Any] = {
        name: real(p, root / name, children, **options)
        for name, (children, options) in shapes.items()
    }
    result["unopened"] = {
        key: outcome(lambda: real(p, root / key, (("x", key, True),)))
        for key in ("Float", "Decimal", "Date", "Timestamp", "UUID")
    }
    return result


def nested(fx, children, *, nullable=False, alone=False):
    """A nested producer over real child bindings; parent shape assembled here."""
    from pietto._project.model import ProjectRowFieldNullability
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_binding as b
    from pietto._project import project_result_contract as c

    contract, artifact, producer = fx["parent"]
    renamed, other = contract.shape.fields
    shape = c.NestedShape(
        None,
        contract.owner,
        contract.output,
        contract.multiplicity,
        contract.ordering,
        tuple(child.field for child in children),
    )
    field = replace(
        renamed if alone else other,
        label="c",
        shape=shape,
        nullability=ProjectRowFieldNullability.NULLABLE
        if nullable
        else ProjectRowFieldNullability.NON_NULL,
    )
    count = b.ProducerObservation(
        field.ordinal,
        "c",
        "postgres",
        "pg_int8",
        0,
        a.MAX_CHILD_ROWS,
        domain="child_count",
    )
    bound = b.ProducerNestedBinding(field, None, count, tuple(children), nullable)
    return b.ProducerResultBinding(
        replace(
            contract,
            shape=c.ResultShape((field,) if alone else (renamed, field)),
        ),
        artifact,
        (bound,) if alone else (producer.fields[0], bound),
    )


def arrow_type(fx, real):
    from pietto._project import project_arrow_result as a
    from pietto._project.project_execution_reader import bind_stored_output

    producer = real["ibt"]
    binding = a.bind_arrow(producer)
    widths = a.bind_arrow(real["widths"])
    # No real upstream yields a NULLABLE container before S16.
    synthetic = nested(fx, fx["ibt"], nullable=True)
    with admitted():
        optional = a.bind_arrow(synthetic)
    field = binding.schema.field("c")
    item = field.type.value_field
    return dict(
        schema=[str(f) for f in binding.schema],
        widths=str(widths.schema.field("c").type),
        nullable=str(optional.schema.field("c")),
        metadata=[
            binding.schema.metadata,
            field.metadata,
            item.metadata,
            *(child.metadata for child in item.type),
        ],
        # Closed and captured lets, and a parent's carried group, bind alike;
        # a stored chunk's binding has the live schema (no protocol facts).
        same=[
            a.bind_arrow(real[name]).schema.equals(binding.schema, check_metadata=True)
            for name in ("closed", "ordered")
        ],
        stored=a.bind_arrow(
            bind_stored_output(producer.output, "postgres_rows")
        ).schema.equals(binding.schema, check_metadata=True),
        authority=outcome(lambda: a.bind_arrow(synthetic)),
    )


def binding_equality(real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_result as a

    producer = real["ibt"]
    binding = a.bind_arrow(producer)
    expected = binding.schema.field("c")
    kids = list(expected.type.value_type)
    struct = pa.struct(kids)

    def lists(item=None, children=None, nullable=False, kind=pa.list_):
        children = kids if children is None else children
        return pa.field(
            "c",
            kind(item or pa.field("item", pa.struct(children), nullable=False)),
            nullable=nullable,
        )

    meta = {b"k": b"v"}
    variants = {
        "element": lists(pa.field("element", struct, nullable=False)),
        "item_metadata": lists(pa.field("item", struct, nullable=False, metadata=meta)),
        "child_metadata": lists(children=[kids[0].with_metadata(meta), *kids[1:]]),
        "item_nullable": lists(pa.field("item", struct, nullable=True)),
        "child_nullable": lists(children=[kids[0].with_nullable(True), *kids[1:]]),
        "child_name": lists(children=[kids[0].with_name("j"), *kids[1:]]),
        "child_order": lists(children=[kids[1], kids[0], kids[2]]),
        "large_string": lists(
            children=[*kids[:2], kids[2].with_type(pa.large_string())]
        ),
        "int8_as_int32": lists(children=[kids[0].with_type(pa.int32()), *kids[1:]]),
        "large_list": lists(kind=pa.large_list),
        "list_view": lists(kind=pa.list_view),
        "container_nullable": lists(nullable=True),
        "field_metadata": expected.with_metadata(meta),
        # PyArrow equality treats {} as no metadata; the binding still refuses it.
        "field_empty_metadata": expected.with_metadata({}),
        "item_empty_metadata": lists(
            pa.field("item", struct, nullable=False).with_metadata({})
        ),
        "child_empty_metadata": lists(children=[kids[0].with_metadata({}), *kids[1:]]),
    }
    observed: dict[str, Any] = {"variants": {}, "requests": {}, "leaves": {}}
    field = producer.fields[1].field
    requests = {
        "integer_widths": a.IntegerWidthRequest(field, 64),
        "text_offset_widths": a.TextOffsetWidthRequest(field, 32),
        "decimal_widths": a.DecimalWidthRequest(field, 128),
        "uuid_representations": a.UUIDRepresentationRequest(field, "uuid"),
        "field_labels": a.ArrowFieldLabelRequest(field, "renamed_c"),
    }
    for name, variant in variants.items():
        bad = replace(binding, schema=pa.schema([binding.schema.field(0), variant]))
        observed["variants"][name] = [
            outcome(lambda: a.verify_arrow_binding(bad, producer)),
            variant.type == expected.type,
        ]
    for name, request in requests.items():
        observed["requests"][name] = outcome(
            lambda: a.bind_arrow(producer, **{name: (None, request)})
        )
    observed["no_requests"] = outcome(
        lambda: a.bind_arrow(producer, **{n: (None, None) for n in requests})
    )
    # Real collected children the rows reader does not open: refused at binding.
    observed["leaves"] = real["unopened"]
    first, bound = producer.fields
    twice = (bound.children[0], bound.children[0], bound.children[2])
    observed["duplicate_child"] = outcome(
        lambda: a.bind_arrow(
            replace(producer, fields=(first, replace(bound, children=twice)))
        )
    )
    return observed


def batch_snapshot(batch):
    column = batch.column(batch.num_columns - 1)
    return dict(
        values=batch.to_pylist(),
        offsets=column.offsets.to_pylist() if len(column) else [],
        offset_type=str(column.offsets.type) if len(column) else None,
        offset=column.offset,
        list_validity=column.buffers()[0] is not None,
        struct_validity=column.values.buffers()[0] is not None,
    )


def owned_values(fx, real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project.project_execution_reader import decode_carrier_rows

    producer = real["ibt"]
    binding = a.bind_arrow(producer)
    batch, usage = a._build_owned_batch_with_usage(binding, ROWS)
    again = a._checked_batch_usage(batch, binding, producer)
    refused = outcome(lambda: a.build_owned_batch(binding, ((1, None),)))
    # No real upstream yields a NULLABLE container before S16.
    optional = nested(fx, fx["ibt"], nullable=True)
    with admitted():
        nbatch = a.build_owned_batch(a.bind_arrow(optional), NULLABLE_ROWS)
    # psycopg-shaped pg_column_arrays_v1 rows, decoded by the rows reader and
    # delivered as an owned batch, for each real shape.
    carrier = {}
    for name in ("ibt", "closed", "ordered"):
        rows, children = decode_carrier_rows(real[name], CARRIER_ROWS, a.MAX_CHILD_ROWS)
        managed = interop.build_managed_batch(a.bind_arrow(real[name]), rows)
        carrier[name] = [children, pa.record_batch(managed).to_pylist()]
        managed.close()
    return dict(
        whole=batch_snapshot(batch),
        usage=list(usage),
        same_checker=list(again) == list(usage),
        nullable=batch_snapshot(nbatch),
        non_null_container=refused,
        carrier=carrier,
        authority=outcome(lambda: a.build_owned_batch(a.bind_arrow(optional), ROWS)),
    )


class _AllocationProbe:
    """Records the PyArrow names a build touches; allocation names must stay unused."""

    def __init__(self, pa):
        self.pa, self.used = pa, set()

    def __getattr__(self, name):
        self.used.add(name)
        return getattr(self.pa, name)


def construction_refusals(real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_result as a

    producer = real["ibt"]
    cases = {
        "container_type": (1, [(1,), (True,), ("x",)]),
        "sequence_type": (1, ("1", (True,), ("x",))),
        "sequence_count": (1, ((1,), (True,))),
        "unequal_lengths": (1, ((1, 2), (True,), ("x",))),
        "int_range": (1, ((99999999999999999999,), (True,), ("x",))),
        "int_bool": (1, ((True,), (True,), ("x",))),
        "text_length": (1, ((1,), (True,), ("x" * 257,))),
        "text_nul": (1, ((1,), (True,), ("a\0b",))),
        "bool_value": (1, ((1,), (1,), ("x",))),
        "nested_element": (1, (([1],), (True,), ("x",))),
        "non_null_child": (1, ((None,), (True,), ("x",))),
        "non_null_container": (1, None),
        "row_arity": (1,),
    }
    observed = {}
    binding = a.bind_arrow(producer)
    for name, row in cases.items():
        probe = _AllocationProbe(pa)
        with patch.object(a, "_arrow", lambda: probe):
            category = outcome(lambda: a.build_owned_batch(binding, (row,)))
        observed[name] = [category, sorted(probe.used & ALLOCATORS)]
    probe = _AllocationProbe(pa)
    with patch.object(a, "_arrow", lambda: probe):
        category = outcome(lambda: a.build_owned_batch(binding, ROWS))
    observed["control"] = [category, sorted(probe.used & ALLOCATORS)]
    return observed


def accounting(real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_result as a
    from pietto._project.project_result_binding import ProducerNestedBinding

    producer, text, wide, wider = (real[k] for k in ("ibt", "text", "wide", "wider"))
    edge = tuple(
        (
            k,
            (
                tuple(range(16 * k, 16 * k + 16)),
                tuple(j % 2 == 0 for j in range(16)),
                ("x" * 256,) * 16,
            ),
        )
        for k in range(64)
    )
    empty = tuple((k, ((), (), ())) for k in range(64))
    observed: dict[str, Any] = {}
    binding = a.bind_arrow(producer)
    observed["s12_edge"] = list(a._build_owned_batch_with_usage(binding, edge)[1])
    observed["empty_children"] = list(
        a._build_owned_batch_with_usage(binding, empty)[1]
    )
    tb = a.bind_arrow(text)
    cap = a.MAX_CHILD_ROWS
    batch, usage = a._build_owned_batch_with_usage(tb, (((("",) * cap,),),))
    observed["child_cap"] = dict(
        accepted=list(usage),
        rows=batch.column(0).offsets.to_pylist(),
        over=outcome(lambda: a.build_owned_batch(tb, (((("",) * (cap + 1),),),))),
        over_allowance=a._base_charge(tb, 1, a.BatchLimits())
        + a._child_charge(
            cast(ProducerNestedBinding, text.fields[0]).children, cap + 1
        ),
    )
    observed["fields_63"] = list(
        a._build_owned_batch_with_usage(a.bind_arrow(wide), ())[1]
    )
    observed["fields_64"] = outcome(
        lambda: a.build_owned_batch(a.bind_arrow(wider), ())
    )
    crowded = ((1, (tuple(range(600)), (True,) * 600, ("x",) * 600)),)
    observed["single_parent"] = outcome(
        lambda: a.build_owned_batch(binding, crowded, limits=a.BatchLimits(bytes=4096))
    )
    # The same parent fits a larger allowance; it is refused whole, never split.
    observed["single_parent_fits"] = list(
        a._build_owned_batch_with_usage(binding, crowded)[1]
    )
    # The meter reaches A before any allocation, a Text child's first
    # offset included: one allowance byte short builds nothing.
    first = (((("ab", "c"),),),)
    observed["first_offset"] = {}
    for allowance in (25, 26):
        probe = _AllocationProbe(pa)
        with patch.object(a, "_arrow", lambda: probe):
            category = outcome(
                lambda: a.build_owned_batch(
                    tb, first, limits=a.BatchLimits(bytes=allowance)
                )
            )
        observed["first_offset"][str(allowance)] = [
            category,
            sorted(probe.used & ALLOCATORS),
        ]
    observed["arrow"] = pa.__version__
    return observed


def zero_length_child(root):
    """Child-interpreter body: zero-length nested columns never reach an accessor."""
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_result as a
    import pietto

    Path(root).mkdir(parents=True)
    producer = real(_product(), Path(root) / "ibt")
    observed: dict[str, Any] = {"pietto": str(Path(pietto.__file__).resolve())}
    binding = a.bind_arrow(producer)
    list_type = binding.schema.field("c").type
    empty = pa.array([], type=list_type.value_type)
    for name, offsets in (("absent", None), ("zero_size", pa.py_buffer(b""))):
        column = pa.Array.from_buffers(list_type, 0, [None, offsets], children=[empty])
        batch = pa.RecordBatch.from_arrays(
            [pa.array([], type=pa.int64()), column], schema=binding.schema
        )
        observed[name] = outcome(
            lambda: observed.__setitem__(
                name + "_usage",
                list(a._checked_batch_usage(batch, binding, producer)),
            )
        )
    print(json.dumps(observed, sort_keys=True))


def _product():
    path = Path(__file__).with_name("_pietto_results_product.py").resolve()
    name = "_pietto_results_product"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def verification(fx, real, root):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_result as a
    import pietto

    producer = real["ibt"]
    # No real upstream yields a NULLABLE container before S16.
    optional = nested(fx, fx["ibt"], nullable=True)
    observed: dict[str, Any] = {"slices": {}, "refusals": {}}
    with admitted():
        nbinding = a.bind_arrow(optional)
    binding = a.bind_arrow(producer)
    batch = a.build_owned_batch(binding, ROWS)
    observed["whole"] = a._checked_batch_usage(batch, binding, producer)[0]
    for start, length in ((1, 2), (3, 1), (4, 0), (0, 0)):
        part = batch.slice(start, length)
        observed["slices"][f"{start}:{length}"] = [
            a._checked_batch_usage(part, binding, producer)[0],
            part.to_pylist(),
        ]
    list_type = binding.schema.field("c").type
    struct_type = list_type.value_type
    kids = list(struct_type)
    leaves = [
        pa.array([1, 2], pa.int64()),
        pa.array([True, False]),
        pa.array(["x", "y"]),
    ]
    good = pa.StructArray.from_arrays(leaves, fields=kids)
    null_element = pa.StructArray.from_arrays(
        leaves, fields=kids, mask=pa.array([False, True])
    )
    null_child = pa.StructArray.from_arrays(
        [pa.array([1, None], pa.int64()), *leaves[1:]], fields=kids
    )

    def offsets(values):
        return pa.array(values, pa.int32()).buffers()[1]

    def supplied(column, schema=None, target=binding):
        parents = pa.array(list(range(len(column))), pa.int64())
        data = pa.RecordBatch.from_arrays(
            [parents, column], schema=schema or binding.schema
        )

        def check():
            return a._checked_batch_usage(data, target, target.producer)

        if target is binding:
            return outcome(check)
        with admitted():
            return outcome(check)

    # An unreferenced null element is not a value, but its bytes are retained.
    unreferenced = pa.RecordBatch.from_arrays(
        [
            pa.array([0], pa.int64()),
            pa.ListArray.from_arrays(
                pa.array([0, 1], pa.int32()), null_element, type=list_type
            ),
        ],
        schema=binding.schema,
    )
    observed["unreferenced_usage"] = list(
        a._checked_batch_usage(unreferenced, binding, producer)
    )
    refusals = observed["refusals"]
    refusals["non_monotonic"] = supplied(
        pa.Array.from_buffers(list_type, 2, [None, offsets([0, 2, 1])], children=[good])
    )
    refusals["null_element"] = supplied(
        pa.ListArray.from_arrays(
            pa.array([0, 2], pa.int32()), null_element, type=list_type
        )
    )
    refusals["null_child"] = supplied(
        pa.ListArray.from_arrays(
            pa.array([0, 2], pa.int32()), null_child, type=list_type
        )
    )
    over_segment = pa.Array.from_buffers(
        list_type,
        2,
        [pa.py_buffer(bytes([0b10])), offsets([0, 1, 2])],
        children=[good],
    )
    refusals["null_container_segment"] = supplied(
        over_segment, nbinding.schema, nbinding
    )
    refusals["null_container_non_null"] = supplied(
        pa.ListArray.from_arrays(
            pa.array([0, 0, 2], pa.int32()),
            good,
            type=list_type,
            mask=pa.array([True, False]),
        )
    )
    item = list_type.value_field
    for name, kind in (
        ("element", pa.list_(item.with_name("element"))),
        ("large_list", pa.large_list(item)),
        ("item_nullable", pa.list_(item.with_nullable(True))),
        (
            "child_metadata",
            pa.list_(
                item.with_type(
                    pa.struct([kids[0].with_metadata({"k": "v"}), *kids[1:]])
                )
            ),
        ),
    ):
        schema = pa.schema(
            [binding.schema.field(0), binding.schema.field(1).with_type(kind)]
        )
        wide = name == "large_list"
        refusals[name] = supplied(
            (pa.LargeListArray if wide else pa.ListArray).from_arrays(
                pa.array([0, 2], pa.int64() if wide else pa.int32()),
                good,
                type=kind,
            ),
            schema,
        )
    view_type = pa.list_view(item)
    view = pa.ListViewArray.from_arrays(
        pa.array([0], pa.int32()), pa.array([2], pa.int32()), good, type=view_type
    )
    refusals["list_view"] = supplied(
        view,
        pa.schema(
            [binding.schema.field(0), binding.schema.field(1).with_type(view_type)]
        ),
    )
    # The batch schema is exact; the column keeps its own item name.
    element = pa.ListArray.from_arrays(
        pa.array([0, 2], pa.int32()),
        good,
        type=pa.list_(item.with_name("element")),
    )
    renamed = pa.RecordBatch.from_arrays(
        [pa.array([0], pa.int64()), element], schema=binding.schema
    )
    observed["column_type_name"] = [
        str(renamed.column(1).type),
        a._checked_batch_usage(renamed, binding, producer)[0],
        renamed.to_pylist(),
    ]
    command = [
        sys.executable,
        *(("-I",) if sys.flags.isolated else ()),
        str(Path(__file__).resolve()),
        "--zero-length-child",
        str(root / "zero-length"),
    ]
    child = subprocess.run(
        command, capture_output=True, text=True, env=os.environ.copy()
    )
    zero_length: dict[str, Any] = dict(
        returncode=child.returncode,
        observed=json.loads(child.stdout)
        if child.returncode == 0
        else child.stderr[-2000:],
    )
    observed["zero_length"] = zero_length
    if child.returncode == 0:
        if zero_length["observed"].pop("pietto") != str(
            Path(pietto.__file__).resolve()
        ):
            raise ValueError("zero-length child imported a foreign product")
    observed["authority"] = outcome(lambda: a.verify_arrow_binding(nbinding, optional))
    return observed


class _Source:
    """Tracks whether owned ingress closed a source it refused."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def guards(real, p):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_ipc as ipc
    from pietto._project import project_result_reader as r

    producer = real["ibt"]
    observed: dict[str, Any] = {}
    binding = a.bind_arrow(producer)
    batch = a.build_owned_batch(binding, ROWS)

    def source():
        return pa.RecordBatchReader.from_batches(binding.schema, [batch])

    observed["manage_batch"] = outcome(lambda: interop.manage_batch(binding, batch))
    observed["import_batch"] = outcome(lambda: interop.import_batch(binding, batch))
    observed["open_finite_reader"] = outcome(
        lambda: r.open_finite_reader(binding, source(), expected_rows=5)
    )
    observed["ingest_reader"] = outcome(
        lambda: ingress.ingest_reader(binding, source(), expected_rows=5)
    )
    observed["import_stream"] = outcome(
        lambda: interop.import_stream(binding, source(), expected_rows=5)
    )
    owned = _Source()
    observed["owned_ingress"] = [
        outcome(
            lambda: ingress._ingest_reader(
                binding, owned, 5, r.FiniteReaderLimits(), None, owned=True
            )
        ),
        owned.closed,
    ]
    # S11 refuses nested IPC before the contract digest until S17.
    observed["encode_ipc"] = outcome(
        lambda: ipc.encode_ipc(binding, source(), expected_rows=5)
    )
    observed["open_ipc"] = outcome(
        lambda: ipc.open_ipc(binding, p.ipc_envelope(b"x", 5), expected_rows=5)
    )
    managed = interop.build_managed_batch(binding, ROWS)
    imported = pa.record_batch(managed)
    observed["build_managed_batch"] = dict(
        policy=managed.buffer_policy,
        usage=managed.usage[0],
        schema=imported.schema.equals(binding.schema, check_metadata=True),
        values=imported.to_pylist() == batch.to_pylist(),
    )
    return observed


def run(p, root, cases):
    root.mkdir(parents=True, exist_ok=True)
    fx = fixtures(p, root / "fixtures", light=True)
    real = real_fixtures(p, root / "real")
    result = {
        GROUPS[0]: arrow_type(fx, real),
        GROUPS[1]: binding_equality(real),
        GROUPS[2]: owned_values(fx, real),
        GROUPS[3]: construction_refusals(real),
        GROUPS[4]: accounting(real),
        GROUPS[5]: verification(fx, real, root),
        GROUPS[6]: guards(real, p),
    }
    # Round-trip through JSON first, as the saved report is checked.
    verify({**cases, **json.loads(json.dumps(result))}, p)
    return result


def exact(actual, expected):
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(
        expected, sort_keys=True, allow_nan=False
    ):
        raise ValueError("nested Arrow evidence")


LIST = "list<item: struct<i: int64 not null, b: bool, t: string> not null>"
VALUES = [
    {"renamed": 7, "c": [{"i": 7, "b": True, "t": "a"}] * 2},
    {"renamed": 7, "c": [{"i": 7, "b": True, "t": "a"}] * 2},
    {"renamed": 0, "c": []},
    {"renamed": 1, "c": [{"i": 5, "b": None, "t": None}]},
    {
        "renamed": 2,
        "c": [{"i": LOW, "b": False, "t": SMILE}, {"i": HIGH, "b": True, "t": ""}],
    },
]
CARRIER_VALUES = [
    {"renamed": 7, "c": [{"i": 7, "b": True, "t": "a"}] * 2},
    {"renamed": 0, "c": []},
    {"renamed": 1, "c": [{"i": 5, "b": None, "t": None}]},
    {
        "renamed": 2,
        "c": [
            {"i": LOW, "b": False, "t": SMILE},
            {"i": HIGH, "b": True, "t": ""},
            {"i": 0, "b": False, "t": "NULL"},
        ],
    },
    {
        "renamed": 3,
        "c": [{"i": 4, "b": False, "t": QUOTED}, {"i": 4, "b": False, "t": "\u00e9"}],
    },
]
# Hand-derived allowances: flat Int ceil(P/8)+8P; nested ceil(P/8)+4(P+1) +
# ceil(C/8) + Int/Bool (ceil(C/8)+8C) + Text (ceil(C/8)+4(C+1)+T).
EXPECTED: dict[str, Any] = {
    GROUPS[0]: dict(
        schema=[
            "pyarrow.Field<renamed: int64 not null>",
            f"pyarrow.Field<c: {LIST} not null>",
        ],
        widths="list<item: struct<w4: int32 not null, w2: int16> not null>",
        nullable=f"pyarrow.Field<c: {LIST}>",
        metadata=[None] * 6,
        same=[True, True],
        stored=True,
        authority="FIELD",
    ),
    GROUPS[1]: dict(
        variants={
            name: [
                "ARROW_BINDING",
                name in ("element", "item_metadata", "child_metadata"),
            ]
            for name in (
                "element",
                "item_metadata",
                "child_metadata",
                "item_nullable",
                "child_nullable",
                "child_name",
                "child_order",
                "large_string",
                "int8_as_int32",
                "large_list",
                "list_view",
            )
        }
        | {
            name: ["ARROW_BINDING", True]
            for name in (
                "container_nullable",
                "field_metadata",
                "field_empty_metadata",
                "item_empty_metadata",
                "child_empty_metadata",
            )
        },
        requests={
            "integer_widths": "ARROW_ADAPTATION",
            "text_offset_widths": "ARROW_ADAPTATION",
            "decimal_widths": "ARROW_ADAPTATION",
            "uuid_representations": "ARROW_ADAPTATION",
            "field_labels": "ARROW_LABELS",
        },
        no_requests="ACCEPTED",
        leaves={
            kind: "PRODUCER_UNSUPPORTED"
            for kind in ("Float", "Decimal", "Date", "Timestamp", "UUID")
        },
        duplicate_child="PRODUCER_FIELDS",
    ),
    GROUPS[2]: dict(
        whole=dict(
            values=VALUES,
            offsets=[0, 2, 4, 4, 5, 7],
            offset_type="int32",
            offset=0,
            list_validity=False,
            struct_validity=False,
        ),
        # P=5, C=7, T=16: 41 + 25 + 1 + 57 + 57 + 49; retained 40 + 24 + 56 +
        # (1 + 1) Bool + (1 + 32 + 16) Text.
        usage=[230, 171],
        same_checker=True,
        nullable=dict(
            values=[
                {"renamed": 1, "c": None},
                {"renamed": 2, "c": [{"i": 3, "b": True, "t": "x"}]},
            ],
            offsets=[0, 0, 1],
            offset_type="int32",
            offset=0,
            list_validity=True,
            struct_validity=False,
        ),
        non_null_container="NULL",
        carrier={name: [8, CARRIER_VALUES] for name in ("ibt", "closed", "ordered")},
        authority="FIELD",
    ),
    GROUPS[3]: {
        **{
            name: [category, []]
            for name, category in (
                ("container_type", "VALUE_DOMAIN"),
                ("sequence_type", "VALUE_DOMAIN"),
                ("sequence_count", "ROW_ARITY"),
                ("unequal_lengths", "ROW_ARITY"),
                ("int_range", "VALUE_DOMAIN"),
                ("int_bool", "VALUE_DOMAIN"),
                ("text_length", "VALUE_DOMAIN"),
                ("text_nul", "VALUE_DOMAIN"),
                ("bool_value", "VALUE_DOMAIN"),
                ("nested_element", "VALUE_DOMAIN"),
                ("non_null_child", "NULL"),
                ("non_null_container", "NULL"),
                ("row_arity", "ROW_ARITY"),
            )
        },
        "control": ["ACCEPTED", ["ListArray", "RecordBatch", "StructArray", "array"]],
    },
    GROUPS[4]: dict(
        # S12 edge: P=64, C=1,024, T=262,144 (DESIGN p8 measured the same R).
        s12_edge=[283928, 275336],
        empty_children=[792, 776],
        # One parent, one Text child of empty strings: 9 + ceil(C/8) +
        # ceil(C/8) + 4(C+1); retained 8 list offsets + 4(C+1) Text offsets.
        child_cap=dict(
            accepted=[4456461, 4194316],
            rows=[0, 1048576],
            over="LIMIT",
            over_allowance=4456467,
        ),
        fields_63=[4, 4],
        fields_64="LIMIT",
        single_parent="LIMIT",
        # P=1, C=600, T=600: 9 + 9 + 75 + 4875 + 4875 + 3079.
        # Retained: 8 + 8 list offsets + 4,800 + 75 Bool + 2,404 + 600 Text.
        single_parent_fits=[12922, 7895],
        # P=1, C=2, T=3: 9 + (1 + 1 + 4 * 3) + 3 = 26 bytes.
        first_offset={
            "25": ["LIMIT", []],
            "26": ["ACCEPTED", ["ListArray", "RecordBatch", "StructArray", "array"]],
        },
        arrow="26.0.0",
    ),
    GROUPS[5]: dict(
        whole=230,
        slices={
            # (P, C, T) = (2, 2, 2), (1, 1, 0), (0, 0, 0), (0, 0, 0).
            "1:2": [80, VALUES[1:3]],
            "3:1": [46, VALUES[3:4]],
            "4:0": [8, []],
            "0:0": [8, []],
        },
        # P=1, C=1, T=1; retained also holds the unreferenced element: 8 + 8 +
        # 1 struct validity + 16 + 1 + (12 + 2).
        unreferenced_usage=[47, 48],
        refusals={
            "non_monotonic": "ARROW_BATCH",
            "null_element": "NULL",
            "null_child": "NULL",
            "null_container_segment": "ARROW_BATCH",
            "null_container_non_null": "NULL",
            "element": "ARROW_SCHEMA",
            "large_list": "ARROW_SCHEMA",
            "item_nullable": "ARROW_SCHEMA",
            "child_metadata": "ARROW_SCHEMA",
            "list_view": "ARROW_SCHEMA",
        },
        column_type_name=[
            "list<element: struct<i: int64 not null, b: bool, t: string> not null>",
            # P=1, C=2, T=2: 9 + 9 + 1 + 17 + 17 + 15.
            68,
            [
                {
                    "renamed": 0,
                    "c": [
                        {"i": 1, "b": True, "t": "x"},
                        {"i": 2, "b": False, "t": "y"},
                    ],
                }
            ],
        ],
        zero_length=dict(
            returncode=0,
            observed={
                "absent": "ACCEPTED",
                "absent_usage": [8, 4],
                "zero_size": "ACCEPTED",
                "zero_size_usage": [8, 4],
            },
        ),
        authority="FIELD",
    ),
    GROUPS[6]: dict(
        manage_batch="ACCEPTED",
        import_batch="ACCEPTED",
        open_finite_reader="ACCEPTED",
        ingest_reader="ACCEPTED",
        import_stream="ACCEPTED",
        # _Source is not a RecordBatchReader; owned ingress still closes it.
        owned_ingress=["READER_SOURCE", True],
        encode_ipc="NESTED_UNAVAILABLE",
        open_ipc="NESTED_UNAVAILABLE",
        build_managed_batch=dict(
            policy="owned_copy", usage=230, schema=True, values=True
        ),
    ),
}


def verify(cases, p):
    """Independent literal expectations; no Arrow import or product rebuild."""
    try:
        for name in GROUPS:
            exact(cases[name], EXPECTED[name])
    except (KeyError, TypeError) as exc:
        raise ValueError("nested Arrow evidence shape") from exc


def damage():
    return (
        lambda v: v["cases"][GROUPS[0]]["schema"].__setitem__(
            1, v["cases"][GROUPS[0]]["schema"][1].replace("item", "element")
        ),
        lambda v: v["cases"][GROUPS[1]]["variants"]["element"].__setitem__(
            0, "ACCEPTED"
        ),
        lambda v: v["cases"][GROUPS[2]]["whole"]["values"][4]["c"][0].update(i=LOW + 1),
        lambda v: v["cases"][GROUPS[2]]["carrier"]["closed"][1][3]["c"][2].update(
            t="null"
        ),
        lambda v: v["cases"][GROUPS[3]]["int_range"][1].append("array"),
        lambda v: v["cases"][GROUPS[4]]["child_cap"].update(over="ACCEPTED"),
        lambda v: v["cases"][GROUPS[5]]["zero_length"].update(returncode=-11),
        lambda v: v["cases"][GROUPS[6]].update(manage_batch="raw:ValueError"),
    )


if __name__ == "__main__":
    if sys.argv[1:2] == ["--zero-length-child"] and len(sys.argv) == 3:
        zero_length_child(sys.argv[2])
    else:
        raise SystemExit("usage: --zero-length-child ROOT")
