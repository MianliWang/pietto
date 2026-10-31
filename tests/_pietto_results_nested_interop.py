"""Phase71 S11 nested copy, lease, C data/stream, zero-row and IPC-closure groups.

Importing the checker layer needs no Arrow. Nested producers are real: S10's
``real`` binds a VERIFIED PostgreSQL Collect (S08) output by the rows reader.
Sources are owned builds over those bindings, carrier rows decoded by the rows
reader (``_carried``), or hand-built foreign SDK batches. Only the NULLABLE
container, which no real upstream yields before S16, keeps S10's one seam
(``admitted()``) and records the category its entry returns without it.
Expected values are hand-written literals. ``delivered`` is also the S11 step
of the D71.11 rows campaign (``_pietto_execution_rows_probe``).
"""

from contextlib import ExitStack, contextmanager, nullcontext
from copy import copy
import gc
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from unittest.mock import patch
import weakref

GROUPS = (
    "nested_copy",
    "nested_copy_refusals",
    "nested_c_array",
    "nested_streams",
    "nested_zero_rows",
    "nested_ipc_closed",
)
# Child rows of each S10 ROWS parent, and two flat parent rows.
CHILDREN = (2, 2, 0, 1, 2)
FLAT_ROWS = ((7, None), (8, 9))
HALF = 1 << 19
IBT = (("i", "Int8", False), ("b", "Bool", True), ("t", "Text", True))
WIDE = tuple((f"c{k}", "Int8", False) for k in range(64))
# Real producers by name: collected children and options (S10 ``real``).
SHAPES = {
    "ibt": (IBT, {}),
    "closed": (IBT, {"closed": True}),
    "no_parents": (IBT, {"where": "rows.id > 100"}),
    "all_empty": (IBT, {"kid_where": "kids.seq > 9"}),
    "text": ((("t", "Text", True),), {"alone": True}),
    "wide": (WIDE[:63], {"alone": True}),
    "wider": (WIDE, {"alone": True}),
}


class _Owner:
    """A lease owner whose lifetime is observable through a weak reference."""


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


def held(managed):
    """The delivered batch a managed handle still holds (never after close)."""
    batch = managed._batch
    assert batch is not None
    return batch


def kids(column):
    """Referenced child rows, read independently; no list accessor at length 0."""
    if not len(column):
        return 0
    offsets = column.offsets.to_pylist()
    return offsets[-1] - offsets[0]


def hexes(column):
    return [None if b is None else b.to_pybytes().hex() for b in column.buffers()]


def _buffers(batch):
    return [b for column in batch.columns for b in column.buffers()]


def _fields(pa, field):
    out = [field]
    if pa.types.is_list(field.type):
        out += _fields(pa, field.type.value_field)
    elif pa.types.is_struct(field.type):
        for child in field.type:
            out += _fields(pa, child)
    return out


def stamped(batch, binding):
    """Every column's own type equals the bound field at every depth."""
    pa = importlib.import_module("pyarrow")
    for column, bound in zip(batch.columns, binding.schema, strict=True):
        actual = _fields(pa, pa.field(bound.name, column.type, bound.nullable))
        expected = _fields(pa, bound)
        if len(actual) != len(expected) or not all(
            x.equals(y, check_metadata=True)
            for x, y in zip(actual, expected, strict=True)
        ):
            return False
    return True


def ownership(source, delivered, leased):
    """Owned: immutable and address-disjoint; leased: shared per buffer position."""
    if leased:
        src, out = _buffers(source), _buffers(delivered)
        return [
            (s is None) == (d is None) and (s is None or s.address == d.address)
            for s, d in zip(src, out, strict=True)
        ]
    used = {b.address for b in _buffers(source) if b is not None and b.size}
    out = [b for b in _buffers(delivered) if b is not None]
    return [
        all(not b.is_mutable for b in out),
        not used & {b.address for b in out if b.size},
    ]


def ipc_read(batch):
    pa = importlib.import_module("pyarrow")
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, batch.schema) as writer:
        writer.write_batch(batch)
    return pa.ipc.open_stream(sink.getvalue()).read_next_batch()


@contextmanager
def counted_closes():
    """Observe (and still perform) every finite-reader source close."""
    from pietto._project import project_result_reader as r

    closes = []
    original = r._close_source

    def close(source):
        closes.append(1)
        original(source)

    with patch.object(r, "_close_source", close):
        yield closes


def delivered(binding, batches):
    """S11 steps over the C exports of one real result, whose handles are
    already closed: each export back through ``import_batch``, every suffix
    slice (the whole batch, each nonzero offset, the zero-length tail) copied
    owned and leased, and all of them through ``import_stream`` and
    ``manage_stream``. Values compare with the exports' own values, which the
    caller checks against its literal oracle; child rows are read
    independently of the product. Every (start, length) slice is the
    ``nested_copy`` matrix's."""
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_result_reader as r

    values = [batch.to_pylist() for batch in batches]
    lists = [i for i, f in enumerate(binding.schema) if pa.types.is_list(f.type)]

    def children(batch):
        return sum(kids(batch.column(i)) for i in lists)

    def facts(managed, expected, source):
        copied = held(managed)
        return [
            children(copied) == children(source),
            stamped(copied, binding),
            pa.record_batch(managed).to_pylist() == expected,
        ]

    imports = [
        k
        for k, batch in enumerate(batches)
        if facts(interop.import_batch(binding, batch), values[k], batch) != [True] * 3
    ]
    failures, count = {}, 0
    for k, batch in enumerate(batches):
        for start in range(batch.num_rows + 1):
            part = batch.slice(start)
            for leased in (False, True):
                count += 1
                lease = (
                    interop.BorrowLease(part, binding, _Owner(), True)
                    if leased
                    else None
                )
                found = facts(
                    interop.manage_batch(binding, part, lease=lease),
                    values[k][start:],
                    part,
                )
                if found != [True] * 3:
                    failures[f"{k}:{start}:{leased}"] = found
    rows = [row for value in values for row in value]

    def source():
        return pa.RecordBatchReader.from_batches(binding.schema, batches)

    entries = {
        "import_stream": lambda: interop.import_stream(
            binding, source(), expected_rows=len(rows)
        ),
        "manage_stream": lambda: interop.manage_stream(
            r.open_finite_reader(binding, source(), expected_rows=len(rows))
        ),
    }
    streams = {}
    for name, open_ in entries.items():
        session = open_()
        found = pa.RecordBatchReader.from_stream(session).read_all().to_pylist()
        session.close()
        streams[name] = [
            session.state,
            found == rows,
            sum(d.child_rows for d in session.input_completion.descriptors),
        ]
    return dict(
        rows=[len(value) for value in values],
        children=sum(children(batch) for batch in batches),
        import_batch=[len(batches), imports],
        slices=[count, failures],
        streams=streams,
    )


def _carried(producer, rows):
    """Carrier rows as the rows reader delivers them (strictly decoded, built
    in batches of 4), each C-exported before its handle closes; values are
    read after a collection, then the S11 steps run on the exports."""
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project.project_execution_reader import decode_carrier_rows

    binding = a.bind_arrow(producer)
    exports = []
    for start in range(0, len(rows), 4):
        part, _ = decode_carrier_rows(
            producer, rows[start : start + 4], a.MAX_CHILD_ROWS
        )
        with interop.build_managed_batch(binding, part) as managed:
            exports.append(pa.record_batch(managed))
    gc.collect()
    return [
        [row for batch in exports for row in batch.to_pylist()],
        delivered(binding, exports),
    ]


def _shapes(pa, binding):
    """Hand-built foreign SDK columns over the bound ``(i, b, t)`` children."""
    list_type = binding.schema.field(1).type
    kinds = list(list_type.value_type)
    good = pa.StructArray.from_arrays(
        [pa.array([1, 2], pa.int64()), pa.array([True, False]), pa.array(["x", "y"])],
        fields=kinds,
    )

    def batch(column, parents=None):
        parents = list(range(len(column))) if parents is None else parents
        return pa.RecordBatch.from_arrays(
            [pa.array(parents, pa.int64()), column], schema=binding.schema
        )

    def listed(offsets, values, kind=list_type, mask=None):
        return pa.ListArray.from_arrays(
            pa.array(offsets, pa.int32()), values, type=kind, mask=mask
        )

    # Every level has its own offset: first list offset 1, struct offset 1,
    # leaves 4/5/2 (Bool at an odd bit offset).
    struct = pa.StructArray.from_arrays(
        [
            pa.array([100, 101, 102, 1, 2, 3, 4, 5, 6], pa.int64()).slice(3),
            pa.array([True] * 4 + [True, False, None, True, False, True]).slice(4),
            pa.array(["z", "a", "bb", None, "dd", "e", "f"]).slice(1),
        ],
        fields=kinds,
    ).slice(1)
    offsets = pa.Array.from_buffers(
        list_type,
        2,
        [None, pa.array([1, 3, 5], pa.int32()).buffers()[1]],
        children=[struct],
    )
    leaves = [pa.array([1, 2], pa.int64()), pa.array([True, False]), good.field(2)]
    hidden = pa.StructArray.from_arrays(
        leaves, fields=kinds, mask=pa.array([False, True])
    )
    item = list_type.value_field
    metadata = pa.struct([kinds[0].with_metadata({"k": "v"}), *kinds[1:]])
    empty = [
        pa.Array.from_buffers(
            f.type,
            0,
            [None, None, pa.py_buffer(b"")]
            if pa.types.is_string(f.type)
            else [None, None],
        )
        for f in kinds
    ]
    return dict(
        offsets=batch(offsets, [10, 11]),
        # B7: a null struct element outside the referenced range.
        hidden=batch(listed([0, 1], hidden), [0]),
        element=batch(listed([0, 2], good, pa.list_(item.with_name("element"))), [0]),
        child_metadata=batch(
            listed([0, 2], good, pa.list_(item.with_type(metadata))), [0]
        ),
        null_element=batch(listed([0, 2], hidden)),
        null_child=batch(
            listed(
                [0, 2],
                pa.StructArray.from_arrays(
                    [pa.array([1, None], pa.int64()), *leaves[1:]], fields=kinds
                ),
            )
        ),
        # B6: all containers [] over zero-length children with absent buffers.
        absent=batch(
            listed([0, 0, 0], pa.StructArray.from_arrays(empty, fields=kinds)),
            [1, 2],
        ),
        over_segment=pa.Array.from_buffers(
            list_type,
            2,
            [pa.py_buffer(bytes([0b10])), pa.array([0, 1, 2], pa.int32()).buffers()[1]],
            children=[good],
        ),
    )


def copies(n, real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a

    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)
    shapes = _shapes(pa, binding)
    observed: dict[str, Any] = {}

    def manage(source, leased=False, entry=interop.manage_batch):
        lease = interop.BorrowLease(source, binding, _Owner(), True) if leased else None
        return entry(binding, source, lease=lease)

    failures, count = {}, 0
    for start in range(6):
        for length in range(6 - start):
            part = batch.slice(start, length)
            for leased in (False, True):
                count += 1
                managed = manage(part, leased)
                facts = [
                    pa.record_batch(managed).to_pylist()
                    == VALUES[start : start + length],
                    stamped(held(managed), binding),
                    kids(held(managed).column(1))
                    == kids(part.column(1))
                    == sum(CHILDREN[start : start + length]),
                    managed.source_usage[0] == managed.usage[0],
                ]
                if facts != [True] * 4:
                    failures[f"{start}:{length}:{leased}"] = facts
    observed["slices"] = [count, failures]
    observed["usage"] = {
        f"{start}:{length}:{leased}": [list(m.source_usage), list(m.usage)]
        for start, length in ((0, 5), (1, 2), (3, 1), (4, 0))
        for leased in (False, True)
        for m in (manage(batch.slice(start, length), leased),)
    }
    named = {
        "whole": batch,
        "offsets": shapes["offsets"],
        "hidden": shapes["hidden"],
    }
    observed["shapes"] = {}
    for name, source in named.items():
        owned, leased = manage(source), manage(source, True)
        observed["shapes"][name] = dict(
            values=pa.record_batch(owned).to_pylist(),
            leased_values=pa.record_batch(leased).to_pylist() == source.to_pylist(),
            children=[kids(held(owned).column(1)), kids(held(leased).column(1))],
            usage=[list(owned.source_usage), list(owned.usage), list(leased.usage)],
            owned=ownership(source, held(owned), False),
            leased=ownership(source, held(leased), True),
            policies=[owned.buffer_policy, leased.buffer_policy],
        )
    joined = pa.concat_batches([batch.slice(1, 2), batch.slice(3, 2)])
    imported = pa.record_batch(interop.build_managed_batch(binding, n.ROWS))
    foreign = {
        "concat": (joined, interop.manage_batch),
        "c_imported_slice": (imported.slice(2, 3), interop.import_batch),
        "ipc_whole": (ipc_read(batch), interop.manage_batch),
        "ipc_slice": (ipc_read(batch.slice(2, 3)), interop.manage_batch),
        "ipc_zero": (ipc_read(batch.slice(4, 0)), interop.manage_batch),
    }
    observed["foreign"] = {}
    for name, (source, entry) in foreign.items():
        managed = manage(source, entry=entry)
        observed["foreign"][name] = [
            pa.record_batch(managed).to_pylist(),
            kids(held(managed).column(1)),
            stamped(held(managed), binding),
        ]
    observed["column_types"] = {
        name: [
            stamped(shapes[name], binding),
            stamped(held(managed), binding),
            pa.record_batch(managed).to_pylist(),
        ]
        for name in ("element", "child_metadata")
        for managed in (manage(shapes[name]),)
    }
    # psycopg-shaped pg_column_arrays_v1 rows (duplicates, [], an all-NULL
    # child row, Int64 limits, quoting) of a captured and a closed Collect:
    # decoded, delivered, then every S11 step, every slice included.
    observed["carrier"] = {
        name: _carried(real[name], n.CARRIER_ROWS) for name in ("ibt", "closed")
    }
    return observed


def copy_refusals(n, fx, real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ingress as ingress
    from pietto._project.project_result_contract import ResultError

    observed: dict[str, Any] = {"before_copy": {}}
    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)
    shapes = _shapes(pa, binding)
    # No real upstream yields a NULLABLE container before S16.
    optional = n.nested(fx, fx["ibt"], nullable=True)
    with n.admitted():
        nbinding = a.bind_arrow(optional)
    over = pa.RecordBatch.from_arrays(
        [pa.array([0, 1], pa.int64()), shapes["over_segment"]],
        schema=nbinding.schema,
    )
    calls = []

    def forbidden(*args):
        calls.append(1)
        raise AssertionError("copy before source check")

    cases = {
        "null_container_segment": (nbinding, over),
        "null_element": (binding, shapes["null_element"]),
        "null_child": (binding, shapes["null_child"]),
        # Positive control: the observer sees a copy of a valid source.
        "control": (binding, batch),
    }
    with patch.object(interop, "_copy_batch", forbidden):
        for name, (target, source) in cases.items():
            calls.clear()
            with n.admitted() if target is nbinding else nullcontext():
                observed["before_copy"][name] = [
                    n.outcome(lambda: interop.manage_batch(target, source)),
                    n.outcome(lambda: interop.import_batch(target, source)),
                    len(calls),
                ]

    def injected(*args):
        raise pa.ArrowInvalid("injected nested copy failure")

    observed["pyarrow_failure"] = ["ACCEPTED"]
    with patch.object(interop, "_nested", injected):
        try:
            interop.manage_batch(binding, batch)
        except ResultError as exc:
            observed["pyarrow_failure"] = [
                exc.category,
                exc.__cause__ is None,
                exc.__context__ is None,
            ]
    original = interop._copy_batch

    def moved(start):
        # A copy bug that moves the referenced range to parents start.. of ROWS.
        return lambda source, lease: original(
            batch.slice(start, source.num_rows), lease
        )

    source = batch.slice(0, 2)
    # Same child count (2), other values: the check is a count law only.
    with patch.object(interop, "_copy_batch", moved(4)):
        same_count = n.outcome(lambda: interop.manage_batch(binding, batch.slice(0, 1)))
    with patch.object(interop, "_copy_batch", moved(2)):
        observed["shifted"] = dict(
            manage_batch=n.outcome(lambda: interop.manage_batch(binding, source)),
            import_batch=n.outcome(lambda: interop.import_batch(binding, source)),
            same_count=same_count,
        )
        stream = ingress.ingest_reader(
            binding,
            pa.RecordBatchReader.from_batches(binding.schema, [source]),
            expected_rows=2,
        )
        foreign = pa.RecordBatchReader.from_stream(stream)
        n.outcome(foreign.read_all)
        foreign.close()
        stream.close()
        observed["shifted"]["stream"] = [
            stream.state,
            getattr(stream.primary_error, "category", None),
        ]
    observed["authority"] = n.outcome(lambda: interop.manage_batch(nbinding, over))
    return observed


def _mutable(pa, binding):
    """A source whose offsets, child Text bytes and child validity stay writable."""
    list_type = binding.schema.field(1).type
    handles = dict(
        offsets=bytearray((0).to_bytes(4, "little") * 3),
        text=bytearray(b"xyyz"),
        validity=bytearray(b"\x07"),
    )
    handles["offsets"][4:12] = (2).to_bytes(4, "little") + (3).to_bytes(4, "little")
    text_offsets = b"".join(v.to_bytes(4, "little") for v in (0, 1, 3, 4))
    struct = pa.StructArray.from_arrays(
        [
            pa.Array.from_buffers(
                pa.int64(),
                3,
                [
                    pa.py_buffer(handles["validity"]),
                    pa.array([1, 2, 3], pa.int64()).buffers()[1],
                ],
            ),
            pa.array([True, False, True]),
            pa.Array.from_buffers(
                pa.string(),
                3,
                [None, pa.py_buffer(text_offsets), pa.py_buffer(handles["text"])],
            ),
        ],
        fields=list(list_type.value_type),
    )
    column = pa.Array.from_buffers(
        list_type, 2, [None, pa.py_buffer(handles["offsets"])], children=[struct]
    )
    source = pa.RecordBatch.from_arrays(
        [pa.array([1, 2], pa.int64()), column], schema=binding.schema
    )
    return source, handles


def c_array(n, real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a

    observed: dict[str, Any] = {}
    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)
    managed = interop.manage_batch(binding, batch)
    grant = managed.transfer()
    observed["spend"] = [
        pa.record_batch(grant).to_pylist() == VALUES,
        n.outcome(lambda: pa.record_batch(grant)),
        n.outcome(lambda: pa.record_batch(copy(managed.transfer()))),
    ]
    item = binding.schema.field(1).type.value_field
    kinds = list(item.type)
    variants = {
        "element": pa.list_(item.with_name("element")),
        "large_list": pa.large_list(item),
        "list_view": pa.list_view(item),
        "item_nullable": pa.list_(item.with_nullable(True)),
        "child_metadata": pa.list_(
            item.with_type(pa.struct([kinds[0].with_metadata({"k": "v"}), *kinds[1:]]))
        ),
    }

    def requested(target, schema):
        capsules = target.__arrow_c_array__(schema.__arrow_c_schema__())
        values = pa.RecordBatch._import_from_c_capsule(*capsules).to_pylist()
        if values != VALUES:
            raise ValueError("requested export values")

    observed["requests"] = {
        "exact_build": n.outcome(
            lambda: requested(
                interop.build_managed_batch(binding, n.ROWS), binding.schema
            )
        ),
        "exact_copy": n.outcome(
            lambda: requested(interop.manage_batch(binding, batch), binding.schema)
        ),
    } | {
        name: n.outcome(
            lambda: requested(
                interop.manage_batch(binding, batch),
                pa.schema(
                    [
                        binding.schema.field(0),
                        binding.schema.field(1).with_type(kind),
                    ]
                ),
            )
        )
        for name, kind in variants.items()
    }
    owner = _Owner()
    alive = weakref.ref(owner)
    part = batch.slice(1, 3)
    leased = interop.manage_batch(
        binding, part, lease=interop.BorrowLease(part, binding, owner, True)
    )
    imported = pa.record_batch(leased)
    leased.close()
    del owner
    gc.collect()
    pinned = alive() is not None
    values = imported.to_pylist() == VALUES[1:4]
    del imported
    gc.collect()
    observed["lifecycle"] = dict(
        pinned_while_import_lives=pinned,
        values_after_close=values,
        released_after_drop=alive() is None,
        transfer_after_close=n.outcome(leased.transfer),
        export_after_close=n.outcome(lambda: pa.record_batch(leased)),
        close_again=n.outcome(leased.close),
    )
    mutations = {
        "control": lambda h: None,
        "offsets": lambda h: h["offsets"].__setitem__(slice(8, 12), bytes(4)),
        "text": lambda h: h["text"].__setitem__(0, 0xFF),
        "validity": lambda h: h["validity"].__setitem__(0, 0b101),
    }
    observed["owner_mutation"] = {}
    for name, mutate in mutations.items():
        source, handles = _mutable(pa, binding)
        target = interop.manage_batch(
            binding,
            source,
            lease=interop.BorrowLease(source, binding, _Owner(), True),
        )
        mutate(handles)
        observed["owner_mutation"][name] = n.outcome(lambda: pa.record_batch(target))
    observed["lease_substitution"] = {}
    for name in ("owner", "non_mutation"):
        lease = interop.BorrowLease(batch, binding, _Owner(), True)
        target = interop.manage_batch(binding, batch, lease=lease)
        if name == "owner":
            object.__setattr__(lease, "owner", _Owner())
        else:
            object.__delattr__(lease, name)
        observed["lease_substitution"][name] = n.outcome(target.transfer)
    return observed


def streams(n, fx, real):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_reader as r

    observed: dict[str, Any] = {}
    flat = a.bind_arrow(fx["parent"][2])
    reader = r.open_finite_reader(
        flat,
        pa.RecordBatchReader.from_batches(
            flat.schema, [a.build_owned_batch(flat, FLAT_ROWS)]
        ),
        expected_rows=2,
    )
    list(reader)
    assert reader.completion is not None
    observed["flat_child_rows"] = [d.child_rows for d in reader.completion.descriptors]
    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)
    canonical = held(interop.manage_batch(binding, batch.slice(4, 0)))
    batches = [batch, batch.slice(2, 3), batch.slice(0, 0), canonical]
    shapes = _shapes(pa, binding)

    def source(items=batches):
        return pa.RecordBatchReader.from_batches(binding.schema, items)

    entries = {
        "ingest_reader": lambda: ingress.ingest_reader(
            binding, source(), expected_rows=8
        ),
        "import_stream": lambda: interop.import_stream(
            binding, source(), expected_rows=8
        ),
        "manage_stream": lambda: interop.manage_stream(
            r.open_finite_reader(binding, source(), expected_rows=8)
        ),
    }
    observed["entries"] = {}
    for name, open_ in entries.items():
        session = open_()
        values = pa.RecordBatchReader.from_stream(session).read_all().to_pylist()
        session.close()
        completion = session.input_completion
        observed["entries"][name] = [
            session.state,
            values == VALUES + VALUES[2:5],
            [d.child_rows for d in completion.descriptors],
            None if name == "import_stream" else [list(d) for d in session.descriptors],
        ]
    session = ingress.ingest_reader(binding, source([]), expected_rows=0)
    foreign = pa.RecordBatchReader.from_stream(session)
    observed["zero_batches"] = [
        foreign.schema.equals(binding.schema, check_metadata=True),
        foreign.read_all().num_rows,
    ]
    session.close()
    observed["zero_batches"].append(session.state)
    item = binding.schema.field(1).type.value_field
    element = pa.schema(
        [
            binding.schema.field(0),
            binding.schema.field(1).with_type(pa.list_(item.with_name("element"))),
        ]
    )
    session = entries["ingest_reader"]()
    refused = n.outcome(
        lambda: session.__arrow_c_stream__(element.__arrow_c_schema__())
    )
    capsule = session.__arrow_c_stream__(binding.schema.__arrow_c_schema__())
    values = pa.RecordBatchReader._import_from_c_capsule(capsule).read_all()
    session.close()
    observed["requests"] = [
        refused,
        values.to_pylist() == VALUES + VALUES[2:5],
        session.state,
    ]
    session = entries["ingest_reader"]()
    session.close()
    observed["closed_incomplete"] = session.state
    with counted_closes() as closes:
        session = ingress.ingest_reader(
            binding, source([batch, shapes["null_element"]]), expected_rows=6
        )
        foreign = pa.RecordBatchReader.from_stream(session)
        n.outcome(foreign.read_all)
        foreign.close()
        session.close()
        observed["failed"] = [
            session.state,
            getattr(session.primary_error, "category", None),
            len(closes),
        ]
    with counted_closes() as closes:
        dropped = entries["ingest_reader"]()
        orphan = dropped._reader
        del dropped
        gc.collect()
        observed["gc_fallback"] = [orphan.state, len(closes)]
    # One Text child of empty strings: 2 x 2^19 rows fit; one more is refused.
    text = a.bind_arrow(real["text"])
    big = a.build_owned_batch(text, (((("",) * HALF,),),))
    one = a.build_owned_batch(text, (((("",),),),))
    with counted_closes() as closes:
        reader = r.open_finite_reader(
            text,
            pa.RecordBatchReader.from_batches(text.schema, [big, big, one]),
            expected_rows=3,
        )
        pulls = [n.outcome(reader.read_next_batch) for _ in range(3)]
        observed["session_cap"] = dict(
            pulls=pulls,
            state=reader.state,
            closes=len(closes),
            children=[row[5] for row in reader._observations],
            counted=reader._children,
        )
    widths = {}
    for name, shape in (("fields_64", "wide"), ("fields_65", "wider")):
        wide = a.bind_arrow(real[shape])
        with counted_closes() as closes:
            found = pa.RecordBatchReader.from_batches(wide.schema, [])
            opened = n.outcome(
                lambda: r.open_finite_reader(wide, found, expected_rows=0).close()
            )
            caller = len(closes)
            owned = n.outcome(
                lambda: ingress._ingest_reader(
                    wide,
                    pa.RecordBatchReader.from_batches(wide.schema, []),
                    0,
                    r.FiniteReaderLimits(),
                    None,
                    owned=True,
                ).close()
            )
            widths[name] = [opened, caller, owned, len(closes) - caller]
    observed["acceptance_width"] = widths
    reader = r.open_finite_reader(
        binding, source([batch, batch.slice(2, 3)]), expected_rows=8
    )
    list(reader)
    completion = reader.completion
    assert completion is not None
    descriptor, second = completion.descriptors

    def verify():
        return n.outcome(
            lambda: r.verify_finite_completion(reader, reader.expectation, completion)
        )

    damage = {"control": verify()}
    for name, value in (("other", 8), ("negative", -1), ("text", "7")):
        object.__setattr__(descriptor, "child_rows", value)
        damage[name] = verify()
        object.__setattr__(descriptor, "child_rows", 7)
    # Coordinated: the total still matches; only the observation differs.
    object.__setattr__(descriptor, "child_rows", 8)
    object.__setattr__(second, "child_rows", 2)
    damage["coordinated"] = verify()
    object.__setattr__(descriptor, "child_rows", 7)
    object.__setattr__(second, "child_rows", 3)
    reader._children = 11
    damage["reader_count"] = verify()
    reader._children = 10
    damage["restored"] = verify()
    observed["completion"] = dict(
        child_rows=[d.child_rows for d in completion.descriptors],
        damage=damage,
    )
    return observed


def zero_rows(n, real, root):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    import pietto

    observed: dict[str, Any] = {}
    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)
    absent = _shapes(pa, binding)["absent"]
    sources = {
        "pyarrow_empty": pa.RecordBatch.from_pylist([], schema=binding.schema),
        "slice": batch.slice(2, 0),
        "ipc_zero": ipc_read(batch.slice(4, 0)),
        "absent_children": absent,
    }
    for name, source in sources.items():
        managed = interop.manage_batch(binding, source)
        observed[name] = dict(
            buffers=hexes(held(managed).column(1)),
            usage=list(managed.usage),
            values=pa.record_batch(managed).to_pylist(),
        )
    observed["absent_children"]["source"] = [
        list(interop.manage_batch(binding, absent).source_usage),
        n.outcome(lambda: pa.record_batch(absent)),
    ]
    # A real result without parent rows, and one whose every collection is []
    # (a zero count and NULL arrays per row, the rows campaign's parents).
    observed["carrier"] = dict(
        no_parents=_carried(real["no_parents"], ()),
        all_empty=_carried(
            real["all_empty"],
            tuple((parent, 0, None, None, None) for parent in (0, 2, 5, 5, -1)),
        ),
    )
    command = [
        sys.executable,
        *(("-I",) if sys.flags.isolated else ()),
        str(Path(__file__).resolve()),
        "--zero-length-copy",
        str(root / "zero-length-copy"),
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
            raise ValueError("zero-length copy child imported a foreign product")
    return observed


def zero_length_copy(root):
    """Child-interpreter body: a zero-length list without offsets is copied."""
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    import pietto

    n = _product()._nested()
    Path(root).mkdir(parents=True)
    observed: dict[str, Any] = {"pietto": str(Path(pietto.__file__).resolve())}
    binding = a.bind_arrow(n.real(_product(), Path(root) / "ibt"))
    list_type = binding.schema.field(1).type
    empty = pa.array([], type=list_type.value_type)
    for name, offsets in (("absent", None), ("zero_size", pa.py_buffer(b""))):
        column = pa.Array.from_buffers(list_type, 0, [None, offsets], children=[empty])
        source = pa.RecordBatch.from_arrays(
            [pa.array([], type=pa.int64()), column], schema=binding.schema
        )
        for leased in (False, True):
            lease = (
                interop.BorrowLease(source, binding, _Owner(), True) if leased else None
            )
            managed = interop.manage_batch(binding, source, lease=lease)
            observed[f"{name}:{leased}"] = [
                hexes(held(managed).column(1)),
                pa.record_batch(managed).num_rows,
            ]
    print(json.dumps(observed, sort_keys=True))


@contextmanager
def observers(names):
    """Each named entry fails on any call and records it (never an authority)."""
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_ipc as ipc

    owners = {
        "contract_digest": ipc,
        "_open_reader": ipc,
        "ingest_reader": ingress,
        "_ingest_reader": ingress,
    }
    calls: list[str] = []

    def observer(name):
        def fail(*args, **kwargs):
            calls.append(name)
            raise AssertionError(name)

        return fail

    with ExitStack() as stack:
        for name in names:
            stack.enter_context(patch.object(owners[name], name, observer(name)))
        yield calls


def ipc_closed(n, fx, real, p):
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ingress as ingress
    from pietto._project import project_result_ipc as ipc
    from pietto._project import project_result_reader as r

    everything = ("contract_digest", "_open_reader", "ingest_reader", "_ingest_reader")
    flat = a.bind_arrow(fx["parent"][2])
    flat_batch = a.build_owned_batch(flat, FLAT_ROWS)

    def flat_source():
        return pa.RecordBatchReader.from_batches(flat.schema, [flat_batch])

    frame = ipc.encode_ipc(flat, flat_source(), expected_rows=2)
    controls = {}
    for name in everything:
        with observers((name,)) as calls:
            if name in ("contract_digest", "ingest_reader"):
                found = n.outcome(
                    lambda: ipc.encode_ipc(flat, flat_source(), expected_rows=2)
                )
            else:
                found = n.outcome(lambda: ipc.open_ipc(flat, frame, expected_rows=2))
            controls[name] = [found, list(calls)]
    observed: dict[str, Any] = {"observer_controls": controls}
    binding = a.bind_arrow(real["ibt"])
    batch = a.build_owned_batch(binding, n.ROWS)

    def source():
        return pa.RecordBatchReader.from_batches(binding.schema, [batch])

    envelope = p.ipc_envelope(b"x", 5)
    with observers(everything) as calls:
        observed["encode_ipc"] = [
            n.outcome(lambda: ipc.encode_ipc(binding, source(), expected_rows=5)),
            list(calls),
        ]
        observed["open_ipc"] = [
            n.outcome(lambda: ipc.open_ipc(binding, envelope, expected_rows=5)),
            list(calls),
        ]
    # The real source-root digest (S07-B) admits the nested contract, so the
    # refusal is the only closure: without it, real nested IPC round-trips.
    observed["digest"] = len(ipc.contract_digest(binding.producer.contract))

    def bypassed(target):
        interop._capture(target)
        return ipc.contract_digest(target.producer.contract)

    with patch.object(ipc, "_contract_digest", bypassed):
        data = ipc.encode_ipc(binding, source(), expected_rows=5)
        stream = ipc.open_ipc(binding, data, expected_rows=5)
        values = pa.RecordBatchReader.from_stream(stream).read_all().to_pylist()
        stream.close()
    observed["without_refusal"] = dict(frame=len(data), values=values == VALUES)
    observed["exports"] = [
        list(module.__all__) for module in (interop, a, r, ingress, ipc)
    ]
    return observed


def run(p, root, cases):
    root.mkdir(parents=True, exist_ok=True)
    n = p._nested()
    fx = n.fixtures(p, root / "fixtures", light=True)
    (root / "real").mkdir()
    real = {
        name: n.real(p, root / "real" / name, children, **options)
        for name, (children, options) in SHAPES.items()
    }
    result = {
        GROUPS[0]: copies(n, real),
        GROUPS[1]: copy_refusals(n, fx, real),
        GROUPS[2]: c_array(n, real),
        GROUPS[3]: streams(n, fx, real),
        GROUPS[4]: zero_rows(n, real, root),
        GROUPS[5]: ipc_closed(n, fx, real, p),
    }
    # Round-trip through JSON first, as the saved report is checked.
    verify({**cases, **json.loads(json.dumps(result))}, p)
    return result


def exact(actual, expected):
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(
        expected, sort_keys=True, allow_nan=False
    ):
        raise ValueError("nested interop evidence")


LOW, HIGH = -(2**63), 2**63 - 1
SMILE = "\U0001f600" * 3
QUOTED = ',{}"\\'
X, Y = {"i": 1, "b": True, "t": "x"}, {"i": 2, "b": False, "t": "y"}
# S10 VALUES, written again: the oracle never comes from the S10 helper.
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
# S10 CARRIER_ROWS as the rows reader delivers them, written again.
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


def steps(batch_rows, children):
    """S11 step facts of a delivered result: k+1 suffix slices of each k-row
    batch, owned and leased; every entry equal; child rows as counted."""
    return dict(
        rows=batch_rows,
        children=children,
        import_batch=[len(batch_rows), []],
        slices=[sum(2 * (k + 1) for k in batch_rows), {}],
        streams={
            name: ["CLOSED", True, children]
            for name in ("import_stream", "manage_stream")
        },
    )


# Canonical empty list<struct<i, b, t>>: list [None, 0000], struct [None],
# i [None, ""], b [None, ""], t [None, 0000, ""].
EMPTY = [None, "00000000", None, None, "", None, "", None, "00000000", ""]
# Hand-derived usage: allowance A as in S10 (flat ceil(P/8)+8P; nested
# ceil(P/8)+4(P+1)+ceil(C/8)+Int/Bool(ceil(C/8)+8C)+Text(ceil(C/8)+4(C+1)+T));
# retained R is the sum of every buffer of every column. A structural copy
# keeps whole buffers, so R changes only where struct validity is dropped or a
# zero-length nested array becomes canonical (flat 40 + offsets 4 + 4 = 48).
EXPECTED: dict[str, Any] = {
    GROUPS[0]: dict(
        slices=[42, {}],
        usage={
            **{
                f"{key}:{leased}": value
                for key, value in (
                    ("0:5", [[230, 171], [230, 171]]),
                    ("1:2", [[80, 171], [80, 171]]),
                    ("3:1", [[46, 171], [46, 171]]),
                    ("4:0", [[8, 171], [8, 48]]),
                )
                for leased in (False, True)
            }
        },
        shapes=dict(
            whole=dict(
                values=VALUES,
                leased_values=True,
                children=[7, 7],
                usage=[[230, 171], [230, 171], [230, 171]],
                owned=[True, True],
                leased=[True] * 12,
                policies=["owned_copy", "borrowed"],
            ),
            # P=2, C=4, T=4: 17 + 13 + 1 + 33 + 33 + 25; R = 16 parents +
            # 12 offsets + 72 i + (2 + 2) b + (1 + 32 + 8) t.
            offsets=dict(
                values=[
                    {
                        "renamed": 10,
                        "c": [
                            {"i": 3, "b": None, "t": None},
                            {"i": 4, "b": True, "t": "dd"},
                        ],
                    },
                    {
                        "renamed": 11,
                        "c": [
                            {"i": 5, "b": False, "t": "e"},
                            {"i": 6, "b": True, "t": "f"},
                        ],
                    },
                ],
                leased_values=True,
                children=[4, 4],
                usage=[[122, 145], [122, 145], [122, 145]],
                owned=[True, True],
                leased=[True] * 12,
                policies=["owned_copy", "borrowed"],
            ),
            # S10's unreferenced null element: the 1-byte struct validity is
            # retained by the source (48) and dropped by every copy (47).
            hidden=dict(
                values=[{"renamed": 0, "c": [X]}],
                leased_values=True,
                children=[1, 1],
                usage=[[47, 48], [47, 47], [47, 47]],
                owned=[True, True],
                leased=[True, True, True, True, False] + [True] * 7,
                policies=["owned_copy", "borrowed"],
            ),
        ),
        foreign=dict(
            concat=[VALUES[1:3] + VALUES[3:5], 5, True],
            c_imported_slice=[VALUES[2:5], 3, True],
            ipc_whole=[VALUES, 7, True],
            ipc_slice=[VALUES[2:5], 3, True],
            ipc_zero=[[], 0, True],
        ),
        column_types={
            name: [False, True, [{"renamed": 0, "c": [X, Y]}]]
            for name in ("element", "child_metadata")
        },
        # Five carrier rows in batches of 4 and 1; child rows 2+0+1+3+2.
        carrier={
            name: [CARRIER_VALUES, steps([4, 1], 8)] for name in ("ibt", "closed")
        },
    ),
    GROUPS[1]: dict(
        before_copy=dict(
            null_container_segment=["ARROW_BATCH", "ARROW_BATCH", 0],
            null_element=["NULL", "NULL", 0],
            null_child=["NULL", "NULL", 0],
            control=["raw:AssertionError", "raw:AssertionError", 2],
        ),
        pyarrow_failure=["ARROW_BATCH", True, True],
        shifted=dict(
            manage_batch="ARROW_BATCH",
            import_batch="ARROW_BATCH",
            same_count="ACCEPTED",
            stream=["FAILED", "ARROW_BATCH"],
        ),
        authority="FIELD",
    ),
    GROUPS[2]: dict(
        spend=[True, "INTEROP_SPENT", "INTEROP_BINDING"],
        requests=dict(
            exact_build="ACCEPTED",
            exact_copy="ACCEPTED",
            element="INTEROP_REQUEST",
            large_list="INTEROP_REQUEST",
            list_view="INTEROP_REQUEST",
            item_nullable="INTEROP_REQUEST",
            child_metadata="INTEROP_REQUEST",
        ),
        lifecycle=dict(
            pinned_while_import_lives=True,
            values_after_close=True,
            released_after_drop=True,
            transfer_after_close="INTEROP_CLOSED",
            export_after_close="INTEROP_CLOSED",
            close_again="ACCEPTED",
        ),
        owner_mutation=dict(
            control="ACCEPTED",
            offsets="ARROW_BATCH",
            text="ARROW_BATCH",
            validity="NULL",
        ),
        lease_substitution=dict(owner="INTEROP_LEASE", non_mutation="INTEROP_LEASE"),
    ),
    GROUPS[3]: dict(
        flat_child_rows=[0],
        entries=dict(
            ingest_reader=[
                "CLOSED",
                True,
                [7, 3, 0, 0],
                [
                    [5, 230, 171, 230, 171, 342],
                    [3, 122, 171, 122, 171, 342],
                    [0, 8, 171, 8, 48, 219],
                    [0, 8, 48, 8, 48, 96],
                ],
            ],
            import_stream=["CLOSED", True, [7, 3, 0, 0], None],
            manage_stream=[
                "CLOSED",
                True,
                [7, 3, 0, 0],
                [
                    [5, 230, 171, 230, 171, 342],
                    [3, 122, 171, 122, 171, 342],
                    [0, 8, 171, 8, 48, 219],
                    [0, 8, 48, 8, 48, 96],
                ],
            ],
        ),
        zero_batches=[True, 0, "CLOSED"],
        requests=["INTEROP_REQUEST", True, "CLOSED"],
        closed_incomplete="CLOSED_INCOMPLETE",
        failed=["FAILED", "NULL", 1],
        gc_fallback=["CLOSED_INCOMPLETE", 1],
        session_cap=dict(
            pulls=["ACCEPTED", "ACCEPTED", "LIMIT"],
            state="FAILED",
            closes=1,
            children=[HALF, HALF],
            counted=2 * HALF,
        ),
        # N_fields = 1 + children; the caller keeps a refused source, owned
        # ingress closes it.
        acceptance_width=dict(
            fields_64=["ACCEPTED", 1, "ACCEPTED", 1],
            fields_65=["LIMIT", 0, "LIMIT", 1],
        ),
        completion=dict(
            child_rows=[7, 3],
            damage=dict(
                control="ACCEPTED",
                other="READER_IDENTITY",
                negative="READER_IDENTITY",
                text="READER_IDENTITY",
                coordinated="READER_IDENTITY",
                reader_count="READER_IDENTITY",
                restored="ACCEPTED",
            ),
        ),
    ),
    GROUPS[4]: dict(
        pyarrow_empty=dict(buffers=EMPTY, usage=[8, 8], values=[]),
        slice=dict(buffers=EMPTY, usage=[8, 48], values=[]),
        ipc_zero=dict(buffers=EMPTY, usage=[8, 8], values=[]),
        # P=2, C=0: 17 + 13 + 4; R = 16 + 12 offsets (+ 4 canonical Text offsets).
        absent_children=dict(
            buffers=[None, "00" * 12, *EMPTY[2:]],
            usage=[34, 32],
            values=[{"renamed": 1, "c": []}, {"renamed": 2, "c": []}],
            source=[[34, 28], "raw:ArrowInvalid"],
        ),
        carrier=dict(
            no_parents=[[], steps([], 0)],
            all_empty=[
                [{"renamed": parent, "c": []} for parent in (0, 2, 5, 5, -1)],
                steps([4, 1], 0),
            ],
        ),
        zero_length=dict(
            returncode=0,
            observed={
                f"{name}:{leased}": [EMPTY, 0]
                for name in ("absent", "zero_size")
                for leased in (False, True)
            },
        ),
    ),
    GROUPS[5]: dict(
        observer_controls={
            name: ["raw:AssertionError", [name]]
            for name in (
                "contract_digest",
                "_open_reader",
                "ingest_reader",
                "_ingest_reader",
            )
        },
        encode_ipc=["NESTED_UNAVAILABLE", []],
        open_ipc=["NESTED_UNAVAILABLE", []],
        digest=32,
        without_refusal=dict(frame=1052, values=True),
        exports=[[], [], [], [], []],
    ),
}


def verify(cases, p):
    """Independent literal expectations; no Arrow import or product rebuild."""
    try:
        for name in GROUPS:
            exact(cases[name], EXPECTED[name])
    except (KeyError, TypeError) as exc:
        raise ValueError("nested interop evidence shape") from exc


def damage():
    return (
        lambda v: v["cases"][GROUPS[0]]["shapes"]["whole"]["usage"][1].__setitem__(
            1, 172
        ),
        lambda v: v["cases"][GROUPS[1]]["before_copy"]["null_element"].__setitem__(
            0, "ACCEPTED"
        ),
        lambda v: v["cases"][GROUPS[2]]["lifecycle"].update(
            pinned_while_import_lives=False
        ),
        lambda v: v["cases"][GROUPS[3]]["entries"]["ingest_reader"][2].__setitem__(
            3, 1
        ),
        lambda v: v["cases"][GROUPS[4]]["slice"]["buffers"].__setitem__(1, ""),
        lambda v: v["cases"][GROUPS[5]]["encode_ipc"].__setitem__(0, "ACCEPTED"),
    )


if __name__ == "__main__":
    if sys.argv[1:2] == ["--zero-length-copy"] and len(sys.argv) == 3:
        zero_length_copy(sys.argv[2])
    else:
        raise SystemExit("usage: --zero-length-copy ROOT")
