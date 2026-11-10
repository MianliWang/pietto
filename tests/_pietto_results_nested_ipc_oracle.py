"""Arrow-free nested IPC case catalog with a pinned-pyarrow self-check.

Each case names the contract it is bound to (``nested``: S10 section 5.6 with
non-null containers; ``nested_nullable``: the same with nullable containers;
``flat``: the scalar parent projection), how a consumer frames it
(``binding``: the bound contract's digest and the declared rows/batches;
``foreign``: the digest of the other canonical contract, nested and flat
swapped; ``unreframed``: frame the payload, then drop ``frame_cut`` trailing
bytes) and the layered category the product must reach. Categories are not
product ``ResultError`` names; S17 maps them. Any REFUSE_* must not report
complete delivery nor echo payload values.

The canonical data is the tie-free FULL result of the literal oracle's
``C6_siblings`` program; the flat contract is its scalar parent projection.
Importing this module never imports pyarrow. Only
``python tests/_pietto_results_nested_ipc_oracle.py --self-check --report P``
builds payloads, with pyarrow 26.0.1 and without pietto.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

import _pietto_execution_nested_oracle as literal

PYARROW = "26.0.1"
CATEGORIES = (
    "ACCEPT",
    "REFUSE_FRAME",
    "REFUSE_CONTRACT",
    "REFUSE_LIMIT",
    "REFUSE_READ",
    "REFUSE_SCHEMA",
    "REFUSE_BATCH",
    "REFUSE_EXTENT",
    "REFUSE_ENCODING",
)
FAMILIES = (
    "truncation",
    "schema",
    "rebatch",
    "offsets",
    "compatibility",
    "discrimination",
)
FRAMINGS = ("binding", "foreign", "unreframed")
BINDINGS = ("nested", "nested_nullable", "flat")
PROGRAM = "C6_siblings"
SET = "FULL"
# S02/S10 per-execution child-row cap; rebind when S10/S11 freeze theirs.
CHILD_CAP = 1_048_576
# Limits the over-cap stream fits so that only the child-row cap refuses it:
# D71.07's default bytes per batch (the reader ceiling is 8 MiB), the session
# byte ceiling and the IPC payload ceiling.
BATCH_BYTES = 1024 * 1024
SESSION_BYTES = 64 * 1024 * 1024
PAYLOAD_BYTES = 96 * 1024 * 1024
OVER_CAP_BATCHES = 16
MAX_PAYLOAD = 64 * 1024
MAX_CORPUS = 4 * 1024 * 1024
EOS = b"\xff\xff\xff\xff\x00\x00\x00\x00"
_METADATA = {b"pietto": b"foreign"}
_EMPTY_PARENT = 2  # canonical parent whose `recent` segment is empty


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    expect: str
    build: Callable[[Any, tuple[str, ...]], Any]
    rows: int
    batches: int
    values: tuple[Any, ...] | None = None
    binding: str = "nested"
    framing: str = "binding"
    frame_cut: int = 0
    input: str = "payload"
    sentinel: bool = True
    child_process: str | None = None
    discriminates: bool = False
    bounded: bool = True
    leaves: tuple[str, ...] = literal.DEFAULT_LEAVES
    # The exact explicit-check problems a REFUSE_BATCH payload carries.
    problems: tuple[str, ...] = ()


# Pure byte operators --------------------------------------------------------


def truncate(data: bytes, end: int) -> bytes:
    if type(end) is not int or not 0 <= end < len(data):
        raise ValueError("truncation must drop at least one byte")
    return data[:end]


def patch_unique(data: bytes, pattern: bytes, replacement: bytes) -> bytes:
    if not pattern or len(pattern) != len(replacement) or pattern == replacement:
        raise ValueError("patch needs a non-empty, same-size, different replacement")
    if data.count(pattern) != 1:
        raise ValueError(
            f"pattern occurs {data.count(pattern)} times, not exactly once"
        )
    return data.replace(pattern, replacement)


def int32s(values: list[int]) -> bytes:
    return struct.pack(f"<{len(values)}i", *values)


def strip_eos(data: bytes) -> bytes:
    if not data.endswith(EOS):
        raise ValueError("payload does not end with the end-of-stream marker")
    return data[: -len(EOS)]


# Canonical data (Arrow-free) ------------------------------------------------


def leaves_of(leaves: tuple[str, ...]) -> tuple[str, ...]:
    leaves = literal.leaves_of(leaves)
    if not set(literal.DEFAULT_LEAVES) <= set(leaves):
        raise ValueError("the IPC catalog needs at least Int, Bool and Text leaves")
    return leaves


def canonical_expected(leaves: tuple[str, ...]) -> tuple[literal.Segment, ...]:
    return literal.expected(PROGRAM, SET, leaves_of(leaves))


def canonical_rows(leaves: tuple[str, ...]) -> list[dict[str, Any]]:
    return literal.example(canonical_expected(leaves))


def flat_rows(leaves: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{"id": row["id"]} for row in canonical_rows(leaves)]


def _layout(leaves: tuple[str, ...]):
    """[(label, type spelling, nullable, children or None)] of the result."""
    tables = literal.seed(SET, leaves)
    spec = literal.program(PROGRAM, leaves).spec
    assert isinstance(spec, literal.Collect)
    fields: list[tuple[str, str | None, bool, tuple | None]] = [
        ("id", "Int", True, None)
    ]
    for let in spec.lets:
        table = tables[let.table]
        children = tuple(
            (n, table.column(n).type, table.column(n).nullable) for n in let.select
        )
        fields.append((let.name, None, False, children))
    return fields


def _copy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {k: [dict(c) for c in v] if type(v) is list else v for k, v in row.items()}
        for row in rows
    ]


def _first_offset_values(leaves):
    rows = _copy(canonical_rows(leaves))
    rows[0]["recent"].pop(0)
    return rows


def _patched_value_values(leaves):
    rows = _copy(canonical_rows(leaves))
    if rows[0]["recent"][0]["v"] != 7:
        raise ValueError("canonical first child value is not 7")
    rows[0]["recent"][0]["v"] = 8
    return rows


def _swapped_parent_values(leaves):
    rows = _copy(canonical_rows(leaves))
    rows[0]["recent"], rows[3]["recent"] = rows[3]["recent"], rows[0]["recent"]
    return rows


def _dropped_duplicate_values(leaves):
    rows = _copy(canonical_rows(leaves))
    paid = rows[3]["paid"]
    if len(paid) < 2 or paid[0] != paid[1]:
        raise ValueError("canonical parent 3 has no duplicate paid child")
    paid.pop(0)
    return rows


def _null_record_values(leaves):
    rows = _copy(canonical_rows(leaves))
    if rows[4]["paid"] != [{"v": None}]:
        raise ValueError("canonical parent 4 paid is not one all-NULL record")
    rows[4]["paid"] = []
    return rows


def _null_container_values(leaves):
    rows = _copy(canonical_rows(leaves))
    if rows[_EMPTY_PARENT]["recent"] != []:
        raise ValueError("canonical parent 2 recent is not empty")
    rows[_EMPTY_PARENT]["recent"] = None
    return rows


def _column_swap_values(leaves):
    rows = _copy(canonical_rows(leaves))
    for row in rows:
        for child in row["recent"]:
            child["v"], child["k"] = child["k"], child["v"]
    return rows


# Arrow construction (pyarrow passed in, never imported here) ---------------


def arrow() -> Any:
    pa = importlib.import_module("pyarrow")
    if pa.__version__ != PYARROW:
        raise SystemExit(f"pyarrow {PYARROW} is required, found {pa.__version__}")
    return pa


def _leaf_type(pa, spelling: str):
    kind = spelling.split("(")[0]
    if kind == "Decimal":
        precision, scale = spelling[len("Decimal(") : -1].split(",")
        return pa.decimal128(int(precision), int(scale))
    return {
        "Int": pa.int64,
        "Bool": pa.bool_,
        "Text": pa.string,
        "Float": pa.float64,
        "Date": pa.date32,
        "Timestamp": lambda: pa.timestamp("us"),
        "UUID": pa.uuid,
    }[kind]()


def canonical_schema(pa, leaves: tuple[str, ...], binding: str = "nested"):
    if binding not in BINDINGS:
        raise ValueError(f"unknown binding {binding}")
    fields = []
    for label, spelling, nullable, children in _layout(leaves_of(leaves)):
        if spelling is not None:
            fields.append(pa.field(label, _leaf_type(pa, spelling), nullable=nullable))
        elif children is not None and binding != "flat":
            item = pa.struct(
                [pa.field(n, _leaf_type(pa, t), nullable=c) for n, t, c in children]
            )
            fields.append(
                pa.field(
                    label,
                    pa.list_(pa.field("item", item, nullable=False)),
                    nullable=nullable or binding == "nested_nullable",
                )
            )
    return pa.schema(fields)


def _column(pa, typ, values: list[Any]):
    if pa.types.is_list(typ) or pa.types.is_large_list(typ):
        offsets, flat = [0], []
        for value in values:
            flat += value or []
            offsets.append(len(flat))
        mask = [value is None for value in values]
        child = _column(pa, typ.value_type, flat)
        cls = pa.LargeListArray if pa.types.is_large_list(typ) else pa.ListArray
        width = pa.int64() if pa.types.is_large_list(typ) else pa.int32()
        return cls.from_arrays(
            pa.array(offsets, width),
            child,
            type=typ,
            mask=pa.array(mask) if any(mask) else None,
        )
    if pa.types.is_struct(typ):
        children = [_column(pa, f.type, [v.get(f.name) for v in values]) for f in typ]
        return pa.StructArray.from_arrays(children, fields=list(typ))
    if typ == pa.uuid():
        values = [None if v is None else v.bytes for v in values]
    return pa.array(values, type=typ)


def _batch(pa, schema, rows: list[dict[str, Any]]):
    return pa.RecordBatch.from_arrays(
        [_column(pa, f.type, [row.get(f.name) for row in rows]) for f in schema],
        schema=schema,
    )


def _write(pa, schema, batches, **options) -> bytes:
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(
        sink,
        schema,
        options=pa.ipc.IpcWriteOptions(
            metadata_version=options.get("version", pa.ipc.MetadataVersion.V5),
            use_legacy_format=options.get("legacy", False),
            allow_64bit=False,
            compression=options.get("compression"),
        ),
    )
    for batch in batches:
        writer.write_batch(batch)
    writer.close()
    return sink.getvalue().to_pybytes()


def boundaries(pa, data: bytes) -> list[int]:
    """End offset of every encapsulated message (schema first)."""
    reader, ends = pa.BufferReader(data), []
    while True:
        try:
            message = pa.ipc.read_message(reader)
        except (OSError, EOFError, pa.ArrowInvalid):
            break
        if message is None:
            break
        ends.append(reader.tell())
    return ends


def _canonical_batch(pa, leaves):
    return _batch(pa, canonical_schema(pa, leaves), canonical_rows(leaves))


def _canonical(pa, leaves, **options) -> bytes:
    return _write(
        pa, canonical_schema(pa, leaves), [_canonical_batch(pa, leaves)], **options
    )


def _per_parent(pa, leaves) -> bytes:
    batch = _canonical_batch(pa, leaves)
    parts = [batch.slice(i, 1) for i in range(batch.num_rows)]
    return _write(pa, batch.schema, parts)


def _rebatched(pa, leaves, cuts: list[tuple[int, int]]) -> bytes:
    batch = _canonical_batch(pa, leaves)
    return _write(pa, batch.schema, [batch.slice(a, n) for a, n in cuts])


def _variant(pa, leaves, name: str) -> bytes:
    schema = canonical_schema(pa, leaves)
    rows = _copy(canonical_rows(leaves))
    index = schema.get_field_index("recent")
    field = schema.field(index)
    item = field.type.value_field
    children = list(item.type)
    position = {f.name: i for i, f in enumerate(children)}

    def with_children(new_children):
        return field.with_type(pa.list_(item.with_type(pa.struct(new_children))))

    def child(label, **change):
        new = list(children)
        old = new[position[label]]
        new[position[label]] = (
            old.with_type(change["type"])
            if "type" in change
            else old.with_name(change["name"])
            if "name" in change
            else old.with_metadata(_METADATA)
        )
        return with_children(new)

    if name == "item_named_element":
        field = field.with_type(pa.list_(item.with_name("element")))
    elif name == "item_nullable":
        field = field.with_type(pa.list_(item.with_nullable(True)))
    elif name == "container_nullable":
        field = field.with_nullable(True)
    elif name == "child_renamed":
        field = child("v", name="w")
        for row in rows:
            for record in row["recent"]:
                record["w"] = record.pop("v")
    elif name == "child_reordered":
        swapped = list(children)
        swapped[position["v"]], swapped[position["k"]] = (
            children[position["k"]],
            children[position["v"]],
        )
        field = with_children(swapped)
    elif name == "child_int32":
        field = child("v", type=pa.int32())
    elif name == "child_large_string":
        field = child("note", type=pa.large_string())
    elif name == "child_dictionary":
        field = child("note", type=pa.dictionary(pa.int32(), pa.string()))
    elif name == "large_list":
        field = field.with_type(pa.large_list(item))
    elif name == "metadata_container":
        field = field.with_metadata(_METADATA)
    elif name == "metadata_item":
        field = field.with_type(pa.list_(item.with_metadata(_METADATA)))
    elif name == "metadata_child":
        field = child("v", metadata=True)
    elif name == "child_missing":
        field = with_children([f for f in children if f.name != "flag"])
    elif name == "child_extra":
        field = with_children([*children, pa.field("extra", pa.int64())])
    elif name == "nested_as_json_text":
        field = pa.field("recent", pa.string(), nullable=False)
        for row in rows:
            row["recent"] = json.dumps(literal.encode(row["recent"]), sort_keys=True)
    elif name != "metadata_schema":
        raise ValueError(f"unknown schema variant {name}")
    schema = schema.set(index, field)
    if name == "metadata_schema":
        schema = schema.with_metadata(_METADATA)
    return _write(pa, schema, [_batch(pa, schema, rows)])


def _flat_payload(pa, leaves) -> bytes:
    schema = canonical_schema(pa, leaves, "flat")
    return _write(pa, schema, [_batch(pa, schema, flat_rows(leaves))])


def _offsets_pattern(pa, leaves, column: str = "recent") -> list[int]:
    return _canonical_batch(pa, leaves).column(column).offsets.to_pylist()


def _patch_offsets(pa, leaves, change: Callable[[list[int]], list[int]]) -> bytes:
    offsets = _offsets_pattern(pa, leaves)
    return patch_unique(
        _canonical(pa, leaves), int32s(offsets), int32s(change(list(offsets)))
    )


def _patch_value(pa, leaves) -> bytes:
    values = _canonical_batch(pa, leaves).column("recent").values.field("v")
    buffer = values.buffers()[1].to_pybytes()
    pattern = buffer[values.offset * 8 : (values.offset + len(values)) * 8]
    replacement = struct.pack("<q", 8) + pattern[8:]
    if pattern[:8] != struct.pack("<q", 7):
        raise ValueError("canonical first child value is not 7")
    return patch_unique(_canonical(pa, leaves), pattern, replacement)


def _rows_payload(pa, leaves, change) -> bytes:
    schema = canonical_schema(pa, leaves)
    return _write(pa, schema, [_batch(pa, schema, change(leaves))])


def _null_container(pa, leaves, parent: int, binding: str) -> bytes:
    """Mask one `recent` container null, keeping its offsets segment."""
    schema = canonical_schema(pa, leaves, binding)
    batch = _batch(pa, schema, canonical_rows(leaves))
    recent = batch.column("recent")
    masked = pa.ListArray.from_arrays(
        recent.offsets,
        recent.values,
        type=recent.type,
        mask=pa.array([i == parent for i in range(len(recent))]),
    )
    return _write(pa, schema, [batch.set_column(1, schema.field(1), masked)])


def _null_in_child(pa, leaves, level: str) -> bytes:
    schema = canonical_schema(pa, leaves)
    batch = _canonical_batch(pa, leaves)
    recent = batch.column("recent")
    struct_values = recent.values
    fields = list(struct_values.type)
    arrays = [struct_values.field(i) for i in range(len(fields))]
    mask = None
    if level == "child":
        ids = arrays[0].to_pylist()
        arrays[0] = pa.array([None, *ids[1:]], type=pa.int64())
    else:
        mask = pa.array([i == 0 for i in range(len(struct_values))])
    rebuilt = pa.StructArray.from_arrays(arrays, fields=fields, mask=mask)
    patched = pa.ListArray.from_arrays(recent.offsets, rebuilt, type=recent.type)
    return _write(pa, schema, [batch.set_column(1, schema.field(1), patched)])


def _zero_offsets(pa, leaves) -> bytes:
    schema = canonical_schema(pa, leaves)
    columns = [pa.array([], type=pa.int64())]
    for field in list(schema)[1:]:
        empty = _column(pa, field.type.value_type, [])
        columns.append(
            pa.Array.from_buffers(
                field.type, 0, [None, pa.py_buffer(b"")], children=[empty]
            )
        )
    return _write(pa, schema, [pa.RecordBatch.from_arrays(columns, schema=schema)])


def _arrow_file(pa, leaves) -> bytes:
    sink = pa.BufferOutputStream()
    batch = _canonical_batch(pa, leaves)
    writer = pa.ipc.new_file(sink, batch.schema)
    writer.write_batch(batch)
    writer.close()
    return sink.getvalue().to_pybytes()


def _over_cap(pa, leaves) -> bytes:
    """CHILD_CAP + 1 Int `paid` children over one-parent batches, `recent` = [].

    Every batch fits the per-batch byte and child limits and the stream fits
    the session and payload byte limits, so only the per-execution child-row
    cap can refuse it.
    """
    schema = canonical_schema(pa, leaves)
    paid_type = schema.field("paid").type
    recent = _column(pa, schema.field("recent").type, [[]])
    total, parts = CHILD_CAP + 1, OVER_CAP_BATCHES
    batches = []
    for i in range(parts):
        n = total // parts + (1 if i < total % parts else 0)
        children = pa.StructArray.from_arrays(
            [pa.array(range(n), pa.int64())], fields=list(paid_type.value_type)
        )
        paid = pa.ListArray.from_arrays(
            pa.array([0, n], pa.int32()), children, type=paid_type
        )
        batches.append(
            pa.RecordBatch.from_arrays(
                [pa.array([i], pa.int64()), recent, paid], schema=schema
            )
        )
    return _write(pa, schema, batches)


# Write-side inputs for encode_ipc (in-memory batches, never bytes).


def _list_slice(pa, leaves):
    return _canonical_batch(pa, leaves).slice(1, 4)


def _struct_offset(pa, leaves, junk: int, sliced: bool):
    batch = _canonical_batch(pa, leaves)
    recent = batch.column("recent")
    values = recent.values
    filler = _column(pa, values.type, [values[0].as_py()] * junk)
    joined = pa.concat_arrays([filler, values])
    if sliced:
        joined, offsets = joined.slice(junk), recent.offsets
    else:
        offsets = pa.array([o + junk for o in recent.offsets.to_pylist()], pa.int32())
    rebuilt = pa.ListArray.from_arrays(offsets, joined, type=recent.type)
    return batch.set_column(1, batch.schema.field(1), rebuilt)


# Catalog --------------------------------------------------------------------


def catalog(leaves: tuple[str, ...] = literal.DEFAULT_LEAVES) -> tuple[Case, ...]:
    leaves = leaves_of(leaves)
    rows = tuple(canonical_rows(leaves))
    n = len(rows)
    cases: list[Case] = []

    def add(name, family, expect, build, **extra):
        extra.setdefault("rows", n)
        extra.setdefault("batches", 1)
        cases.append(Case(name, family, expect, build, leaves=leaves, **extra))

    canonical = _canonical
    # truncation
    add(
        "truncate_after_schema",
        "truncation",
        "REFUSE_EXTENT",
        lambda pa, lv: truncate(
            canonical(pa, lv), boundaries(pa, canonical(pa, lv))[0]
        ),
        sentinel=False,
    )
    add(
        "truncate_after_second_batch",
        "truncation",
        "REFUSE_EXTENT",
        lambda pa, lv: truncate(
            _per_parent(pa, lv), boundaries(pa, _per_parent(pa, lv))[2]
        ),
        batches=n,
        sentinel=False,
    )
    add(
        "truncate_mid_metadata",
        "truncation",
        "REFUSE_READ",
        lambda pa, lv: truncate(
            canonical(pa, lv), boundaries(pa, canonical(pa, lv))[0] + 16
        ),
        sentinel=False,
    )
    add(
        "truncate_mid_body",
        "truncation",
        "REFUSE_READ",
        lambda pa, lv: truncate(
            canonical(pa, lv), boundaries(pa, canonical(pa, lv))[1] - 1
        ),
    )
    add(
        "truncate_unreframed",
        "truncation",
        "REFUSE_FRAME",
        canonical,
        framing="unreframed",
        frame_cut=16,
    )
    add("declared_rows_mismatch", "truncation", "REFUSE_EXTENT", canonical, rows=n + 1)
    add(
        "declared_batches_mismatch", "truncation", "REFUSE_EXTENT", canonical, batches=2
    )
    add(
        "missing_eos",
        "truncation",
        "ACCEPT",
        lambda pa, lv: strip_eos(canonical(pa, lv)),
        values=rows,
    )
    # schema
    for variant in (
        "item_named_element",
        "item_nullable",
        "container_nullable",
        "child_renamed",
        "child_reordered",
        "child_int32",
        "child_large_string",
        "child_dictionary",
        "large_list",
        "metadata_container",
        "metadata_item",
        "metadata_child",
        "metadata_schema",
        "child_missing",
        "child_extra",
        "nested_as_json_text",
    ):
        add(
            variant,
            "schema",
            "REFUSE_SCHEMA",
            lambda pa, lv, v=variant: _variant(pa, lv, v),
        )
    add(
        "flat_payload_nested_binding",
        "schema",
        "REFUSE_SCHEMA",
        _flat_payload,
        sentinel=False,
    )
    add(
        "nested_payload_flat_binding",
        "schema",
        "REFUSE_SCHEMA",
        canonical,
        binding="flat",
    )
    # rebatch
    add("single_batch", "rebatch", "ACCEPT", canonical, values=rows)
    add("batch_per_parent", "rebatch", "ACCEPT", _per_parent, batches=n, values=rows)
    add(
        "interleaved_empty_batch",
        "rebatch",
        "ACCEPT",
        lambda pa, lv: _rebatched(pa, lv, [(0, 2), (2, 0), (2, n - 2)]),
        batches=3,
        values=rows,
    )
    add(
        "zero_row_batch",
        "rebatch",
        "ACCEPT",
        lambda pa, lv: _rebatched(pa, lv, [(0, 0)]),
        rows=0,
        values=(),
        sentinel=False,
    )
    add(
        "zero_batches",
        "rebatch",
        "ACCEPT",
        lambda pa, lv: _rebatched(pa, lv, []),
        rows=0,
        batches=0,
        values=(),
        sentinel=False,
    )
    # offsets
    add(
        "write_list_slice",
        "offsets",
        "ACCEPT",
        _list_slice,
        rows=4,
        values=rows[1:5],
        input="batch",
    )
    add(
        "write_struct_offset",
        "offsets",
        "ACCEPT",
        lambda pa, lv: _struct_offset(pa, lv, 1, True),
        values=rows,
        input="batch",
    )
    add(
        "write_nonzero_first_offset",
        "offsets",
        "ACCEPT",
        lambda pa, lv: _struct_offset(pa, lv, 2, False),
        values=rows,
        input="batch",
    )
    add(
        "read_nonzero_first_offset",
        "offsets",
        "ACCEPT",
        lambda pa, lv: _patch_offsets(pa, lv, lambda o: [1, *o[1:]]),
        values=tuple(_first_offset_values(leaves)),
    )
    add(
        "offsets_decreasing",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _patch_offsets(pa, lv, lambda o: [o[0], o[2] + 1, *o[2:]]),
        child_process="validate",
    )
    add(
        "offsets_beyond_child",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _patch_offsets(pa, lv, lambda o: [*o[:-1], o[-1] + 5]),
        child_process="validate",
    )
    # Each null-container rule alone: field nullability over an empty segment;
    # a nullable container that still owns children; the valid null control.
    add(
        "null_container_in_nonnull_field",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _null_container(pa, lv, _EMPTY_PARENT, "nested"),
        problems=("recent: null in a non-nullable field",),
    )
    add(
        "null_container_nonempty_segment",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _null_container(pa, lv, 0, "nested_nullable"),
        binding="nested_nullable",
        problems=("recent[0]: null container owns children",),
    )
    add(
        "null_container_empty_segment",
        "offsets",
        "ACCEPT",
        lambda pa, lv: _null_container(pa, lv, _EMPTY_PARENT, "nested_nullable"),
        binding="nested_nullable",
        values=tuple(_null_container_values(leaves)),
    )
    add(
        "null_in_nonnull_child",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _null_in_child(pa, lv, "child"),
        problems=("recent.id: null child",),
    )
    add(
        "null_item",
        "offsets",
        "REFUSE_BATCH",
        lambda pa, lv: _null_in_child(pa, lv, "item"),
        problems=("recent: null item",),
    )
    add(
        "zero_length_offsets_buffer",
        "offsets",
        "ACCEPT",
        _zero_offsets,
        rows=0,
        values=(),
        sentinel=False,
        child_process="zero_offsets",
    )
    # compatibility
    for codec in ("zstd", "lz4"):
        add(
            f"compression_{codec}",
            "compatibility",
            "REFUSE_ENCODING",
            lambda pa, lv, c=codec: canonical(pa, lv, compression=c),
            sentinel=False,
        )
    add(
        "legacy_format",
        "compatibility",
        "ACCEPT",
        lambda pa, lv: canonical(pa, lv, legacy=True),
        values=rows,
    )
    add(
        "metadata_v4",
        "compatibility",
        "ACCEPT",
        lambda pa, lv: canonical(pa, lv, version=pa.ipc.MetadataVersion.V4),
        values=rows,
    )
    add("arrow_file_format", "compatibility", "REFUSE_READ", _arrow_file)
    add(
        "foreign_flat_digest",
        "compatibility",
        "REFUSE_CONTRACT",
        canonical,
        framing="foreign",
    )
    add(
        "foreign_nested_digest",
        "compatibility",
        "REFUSE_CONTRACT",
        _flat_payload,
        binding="flat",
        framing="foreign",
        sentinel=False,
    )
    if leaves == literal.DEFAULT_LEAVES:
        # The only payload over 64 KiB: the cap is a child-row count, so it
        # is built once, with the narrowest leaves, outside the size budget.
        add(
            "child_rows_over_cap",
            "compatibility",
            "REFUSE_LIMIT",
            _over_cap,
            rows=OVER_CAP_BATCHES,
            batches=OVER_CAP_BATCHES,
            sentinel=False,
            bounded=False,
        )
    # discrimination: the digest is no authentication, so the product accepts
    # these; the comparator must still tell them from the canonical values.
    for name, build, change in (
        ("patched_value_7_to_8", _patch_value, _patched_value_values),
        (
            "children_swapped_between_parents",
            lambda pa, lv: _rows_payload(pa, lv, _swapped_parent_values),
            _swapped_parent_values,
        ),
        (
            "duplicate_child_dropped",
            lambda pa, lv: _rows_payload(pa, lv, _dropped_duplicate_values),
            _dropped_duplicate_values,
        ),
        (
            "all_null_record_as_empty",
            lambda pa, lv: _rows_payload(pa, lv, _null_record_values),
            _null_record_values,
        ),
        (
            "same_type_column_swap",
            lambda pa, lv: _rows_payload(pa, lv, _column_swap_values),
            _column_swap_values,
        ),
    ):
        add(
            name,
            "discrimination",
            "ACCEPT",
            build,
            values=tuple(change(leaves)),
            discriminates=True,
        )
    return tuple(cases)


# Self-check (pyarrow only) ----------------------------------------------------

_CHILD = r"""
import importlib, json, sys
pa = importlib.import_module("pyarrow")
data, out = sys.stdin.buffer.read(), {}
try:
    batches = list(pa.ipc.open_stream(data))
    out["rows"] = sum(b.num_rows for b in batches)
    out["batches"] = len(batches)
    if sys.argv[1] == "validate":
        for b in batches:
            b.validate(full=True)
        out["validated"] = True
    else:
        for b in batches:
            b.validate(full=True)
        out["offset_bytes"] = [
            c.buffers()[1].size for b in batches for c in b.columns
            if pa.types.is_list(c.type)
        ]
except Exception as error:
    out["error"] = type(error).__name__
print(json.dumps(out, sort_keys=True))
"""


def _child(mode: str, data: bytes) -> dict[str, Any]:
    done = subprocess.run(
        [sys.executable, "-P", "-c", _CHILD, mode],
        input=data,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if done.returncode != 0:
        return {"crashed": done.returncode}
    return json.loads(done.stdout)


def _read(pa, data: bytes) -> tuple[Any, list[Any]]:
    reader = pa.ipc.open_stream(data)
    return reader.schema, list(reader)


def _rows(batches) -> list[Any]:
    return [row for batch in batches for row in batch.to_pylist()]


def _nullability(pa, batch) -> list[str]:
    """Explicit checks validate(full=True) does not make (A3/A4)."""
    problems = []
    for field, column in zip(batch.schema, batch.columns, strict=True):
        if not field.nullable and column.null_count:
            problems.append(f"{field.name}: null in a non-nullable field")
        if pa.types.is_list(field.type) and len(column):
            offsets = column.offsets.to_pylist()
            for i, valid in enumerate(column.is_valid().to_pylist()):
                if not valid and offsets[i] != offsets[i + 1]:
                    problems.append(f"{field.name}[{i}]: null container owns children")
            values = column.values.slice(offsets[0], offsets[-1] - offsets[0])
            if not field.type.value_field.nullable and values.null_count:
                problems.append(f"{field.name}: null item")
            for i, child_field in enumerate(field.type.value_type):
                if not child_field.nullable and values.field(i).null_count:
                    problems.append(f"{field.name}.{child_field.name}: null child")
    return problems


def _referenced(column):
    """Struct children a list column's offsets reference (S10 DESIGN 5.7)."""
    offsets = column.offsets.to_pylist() if len(column) else [0]
    return column.values.slice(offsets[0], offsets[-1] - offsets[0])


def _charge(pa, batch) -> tuple[int, int]:
    """(child rows C, max(allowance A, retained R)) of one batch, S10 DESIGN 5.7."""

    def leaf(array) -> int:
        n = len(array)
        if pa.types.is_string(array.type):
            text = sum(len(v.encode()) for v in array.to_pylist() if v is not None)
            return -(-n // 8) + 4 * (n + 1) + text
        if not (pa.types.is_int64(array.type) or pa.types.is_boolean(array.type)):
            raise ValueError(f"no allowance rule for {array.type}")
        return -(-n // 8) + 8 * n

    children = allowance = 0
    for column in batch.columns:
        if not pa.types.is_list(column.type):
            allowance += leaf(column)
            continue
        values, p = _referenced(column), len(column)
        children += len(values)
        allowance += -(-p // 8) + 4 * (p + 1) + -(-len(values) // 8)
        allowance += sum(leaf(values.field(i)) for i in range(values.type.num_fields))
    retained = sum(
        buffer.size
        for column in batch.columns
        for buffer in column.buffers()
        if buffer is not None
    )
    return children, max(allowance, retained)


def _same(found: list[Any], want: tuple[Any, ...] | None) -> bool:
    return literal.encode(list(found)) == literal.encode(list(want or ()))


def _verify(pa, case: Case, built: Any, schemas: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_schema = schemas[case.binding]
    if case.input == "batch":
        batch = built
        batch.validate(full=True)
        recent = batch.column("recent")
        if case.name == "write_list_slice" and recent.offset == 0:
            errors.append("list slice has no array offset")
        if case.name == "write_struct_offset" and recent.values.offset == 0:
            errors.append("struct child has no offset")
        if case.name == "write_nonzero_first_offset" and recent.offsets[0].as_py() == 0:
            errors.append("first list offset is zero")
        if not _same(batch.to_pylist(), case.values):
            errors.append("in-memory values differ from the oracle")
        _, back = _read(pa, _write(pa, batch.schema, [batch]))
        if not _same(_rows(back), case.values):
            errors.append("written values differ from the oracle")
        return errors
    data = built
    if case.sentinel and literal.SENTINEL.encode() not in data:
        errors.append("sentinel-marked payload lacks the sentinel")
    if (
        case.sentinel
        and case.expect == "ACCEPT"
        and literal.SENTINEL not in repr(case.values)
    ):
        errors.append("sentinel-marked values lack the sentinel")
    if case.child_process is not None:
        result = _child(case.child_process, data)
        if "crashed" in result:
            return [f"child process died with {result['crashed']}"]
        if case.expect == "REFUSE_BATCH" and "error" not in result:
            errors.append("validate(full=True) accepted a damaged offsets buffer")
        if case.expect == "ACCEPT" and (
            "error" in result or result.get("offset_bytes") != [0, 0] or result["rows"]
        ):
            errors.append(f"zero-length offsets payload not as built: {result}")
        return errors
    if case.expect == "REFUSE_READ":
        try:
            _read(pa, data)
        except (OSError, pa.ArrowInvalid):
            return errors
        return errors + ["pyarrow read a REFUSE_READ payload"]
    schema, batches = _read(pa, data)
    rows, count = _rows(batches), len(batches)
    if case.expect == "REFUSE_SCHEMA":
        if schema.equals(expected_schema, check_metadata=True):
            errors.append("schema variant equals the bound schema")
        if case.name == "item_named_element":
            field = schema.field("recent")
            canonical = expected_schema.field("recent")
            if not (
                field.type == canonical.type
                and not field.equals(canonical, check_metadata=True)
            ):
                errors.append("element naming is not DataType-equal but Field-unequal")
        return errors
    if not schema.equals(expected_schema, check_metadata=True):
        errors.append("payload schema differs from the bound schema")
    if case.expect == "REFUSE_EXTENT":
        if (len(rows), count) == (case.rows, case.batches):
            errors.append("declared extent equals the payload extent")
    elif case.expect == "REFUSE_BATCH":
        found = sorted(p for batch in batches for p in _nullability(pa, batch))
        if not case.problems or found != sorted(case.problems):
            errors.append(f"explicit checks found {found}, not {list(case.problems)}")
    elif case.expect == "REFUSE_LIMIT":
        charges = [_charge(pa, batch) for batch in batches]
        for batch in batches:
            batch.validate(full=True)
            errors += _nullability(pa, batch)
        if (len(rows), count) != (case.rows, case.batches):
            errors.append("declared extent differs from the payload extent")
        if sum(c for c, _ in charges) <= CHILD_CAP:
            errors.append("child rows do not exceed the cap")
        if any(c > CHILD_CAP or b > BATCH_BYTES for c, b in charges):
            errors.append("a batch alone exceeds a per-batch limit")
        if sum(b for _, b in charges) > SESSION_BYTES or len(data) > PAYLOAD_BYTES:
            errors.append("the stream exceeds a byte limit")
    elif case.expect in {"REFUSE_ENCODING", "REFUSE_FRAME", "REFUSE_CONTRACT"}:
        if not _same(
            rows,
            tuple(
                flat_rows(case.leaves)
                if case.binding == "flat"
                else canonical_rows(case.leaves)
            ),
        ):
            errors.append("payload values differ from the canonical values")
        if case.expect == "REFUSE_FRAME" and not 0 < case.frame_cut < len(data):
            errors.append("frame cut outside the payload")
    elif case.expect == "ACCEPT":
        for batch in batches:
            batch.validate(full=True)
            errors += _nullability(pa, batch)
        if (len(rows), count) != (case.rows, case.batches):
            errors.append("declared extent differs from the payload extent")
        if not _same(rows, case.values):
            errors.append("read values differ from the oracle values")
        if (
            case.name == "read_nonzero_first_offset"
            and batches[0].column("recent").offsets[0].as_py() == 0
        ):
            errors.append("patched payload has a zero first offset")
        if case.name == "missing_eos" and data.endswith(EOS):
            errors.append("payload still ends with EOS")
        canonical = tuple(canonical_rows(case.leaves))
        verdict = literal.check(rows, canonical_expected(case.leaves))
        if case.discriminates and (not verdict or _same(rows, canonical)):
            errors.append("comparator accepts damaged values")
        if not case.discriminates and _same(rows, canonical) and verdict:
            errors.append("comparator rejects canonical values")
    return errors


def _expected_schema(pa, leaves: tuple[str, ...], nullable: bool):
    """Section 5.2 restated by hand, independent of canonical_schema()."""
    extra = {
        "Float": pa.field("ratio", pa.float64()),
        "Decimal": pa.field("price", pa.decimal128(18, 4)),
        "Date": pa.field("ship_day", pa.date32()),
        "Timestamp": pa.field("seen_at", pa.timestamp("us")),
        "UUID": pa.field("token", pa.uuid()),
    }
    recent = [
        pa.field("id", pa.int64(), nullable=False),
        pa.field("v", pa.int64()),
        pa.field("k", pa.int64()),
        pa.field("flag", pa.bool_()),
        pa.field("note", pa.string()),
        *[extra[name] for name in leaves if name in extra],
    ]
    paid = [pa.field("v", pa.int64())]
    return pa.schema(
        [
            pa.field("id", pa.int64()),
            pa.field(
                "recent",
                pa.list_(pa.field("item", pa.struct(recent), nullable=False)),
                nullable=nullable,
            ),
            pa.field(
                "paid",
                pa.list_(pa.field("item", pa.struct(paid), nullable=False)),
                nullable=nullable,
            ),
        ]
    )


def self_check(report: Path) -> int:
    pa = arrow()
    entries, total, failed = [], 0, False
    for leaves in (literal.DEFAULT_LEAVES, literal.LEAVES):
        schemas = {
            binding: canonical_schema(pa, leaves, binding) for binding in BINDINGS
        }
        for binding, nullable in (("nested", False), ("nested_nullable", True)):
            if not schemas[binding].equals(
                _expected_schema(pa, leaves, nullable), check_metadata=True
            ):
                entries.append(
                    {"leaves": list(leaves), "name": f"{binding}_schema", "ok": False}
                )
                failed = True
        for case in catalog(leaves):
            built = case.build(pa, leaves)
            errors: list[str] = []
            entry: dict[str, Any] = {
                "binding": case.binding,
                "expect": case.expect,
                "family": case.family,
                "leaves": list(leaves),
                "name": case.name,
            }
            if case.input == "payload":
                if built != case.build(pa, leaves):
                    errors.append("payload bytes are not deterministic")
                entry["bytes"] = len(built)
                entry["sha256"] = hashlib.sha256(built).hexdigest()
                if case.bounded:
                    total += len(built)
                    if len(built) > MAX_PAYLOAD:
                        errors.append("payload exceeds 64 KiB")
            try:
                errors += _verify(pa, case, built, schemas)
            except Exception as error:  # a self-check failure, never a pass
                errors.append(f"self-check raised {type(error).__name__}")
            entry["errors"] = errors
            entry["ok"] = not errors
            failed = failed or bool(errors)
            entries.append(entry)
    document = {
        "corpus_bytes": total,
        "corpus_within_limit": total <= MAX_CORPUS,
        "entries": entries,
        "format": "pietto.nested-ipc-oracle-self-check.v1",
        "ok": not failed and total <= MAX_CORPUS,
        "pyarrow": pa.__version__,
    }
    report.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    return 0 if document["ok"] else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", required=True)
    parser.add_argument("--report", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if "pietto" in sys.modules:
        raise SystemExit("the IPC oracle self-check runs without pietto")
    sys.modules["pietto"] = None  # type: ignore[assignment]
    return self_check(arguments.report)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
