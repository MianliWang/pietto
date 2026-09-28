"""Small whole-result laws. Importing the observation/checker layer needs no Arrow."""

from collections import Counter
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from typing import Any
from unittest.mock import patch

GROUPS = (
    "whole_routes_values",
    "whole_rechunk_bag_order",
    "whole_fields_adaptation",
    "whole_live_authority",
    "whole_finite_completion",
    "whole_lifetime_delivery",
    "whole_ipc_integrity",
    "whole_resource_boundaries",
    "whole_historical_contracts",
    "whole_oracle_discrimination",
)
KINDS = (
    "int",
    "int",
    "int",
    "bool",
    "float64",
    "utf8",
    "utf8",
    "decimal",
    "decimal",
    "civil_us",
    "uuid",
    "uuid",
    "int",
)
STATES = ("values", "empty", "null", "first_null")
LAYOUTS = ((4,), (1, 3), (0, 1, 0, 3, 0))
MUTATIONS = (
    "value",
    "signed_zero",
    "column_swap",
    "reorder",
    "duplicate_loss",
    "duplicate_replacement",
    "null",
)


def exact(actual, expected):
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(
        expected, sort_keys=True, allow_nan=False
    ):
        raise ValueError("whole-result correspondence")


def tagged(rows):
    """Position and scalar tags prevent bool/int/NULL or display equality."""
    result = []
    for row in rows:
        if len(row) != 13:
            raise ValueError("whole-result arity")
        values = []
        for i, (kind, value) in enumerate(zip(KINDS, row, strict=True)):
            if value is None:
                values.append(["null"])
                continue
            expected_type = (
                bool if kind == "bool" else int if kind in ("int", "civil_us") else str
            )
            if type(value) is not expected_type:
                raise ValueError("whole-result scalar type")
            values.append(
                [kind, value, 2 if i == 7 else 30]
                if kind == "decimal"
                else [kind, value]
            )
        result.append(values)
    return result


def bag(rows):
    return Counter(
        json.dumps(row, separators=(",", ":"), allow_nan=False) for row in rows
    )


def changed(rows, mutation):
    rows = deepcopy(rows)
    if mutation == "value":
        rows[0][0] = 17
    elif mutation == "signed_zero":
        rows[0][4] = "0000000000000000"
    elif mutation == "column_swap":
        for row in rows:
            row[0], row[12] = row[12], row[0]
    elif mutation == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "duplicate_loss":
        rows.pop()
    elif mutation == "duplicate_replacement":
        rows[-1] = list(rows[1])
    elif mutation == "null":
        rows[0][1] = None
    else:
        raise ValueError("unknown whole-result mutation")
    return rows


def expected(p, state="values", *, alternative=False):
    value = p.finite_expected(
        state=state, all_nullable=state in ("null", "first_null"), wide=alternative
    )
    if alternative:
        value["fields"][0]["type"] = "int32"
        value["fields"][10]["type"] = "fixed_size_binary[16]"
    else:
        value["fields"][10]["metadata"] = {}
    value["rows"] = tagged(value["rows"])
    return value


def observe(p, batch):
    value = p.finite_snapshot(batch)
    value["rows"] = tagged(value["rows"])
    return value


def fragments(batch, layout):
    assert sum(layout) == batch.num_rows and len(layout) <= 8
    offset = 0
    result = []
    for size in layout:
        result.append(batch.slice(offset, size))
        offset += size
    return result


def allowance(rows, *, wide=False):
    """Authored physical arithmetic, independent of production admission helpers."""
    count = len(rows)
    fixed = 6 * 8 + 16 + 32 + 2 * 16 + 8 + (16 if wide else 0)
    return (
        13 * ((count + 7) // 8)
        + fixed * count
        + (16 if wide else 12) * (count + 1)
        + sum(
            len(bytes.fromhex(row[i]))
            for row in rows
            for i in (5, 6)
            if row[i] is not None
        )
    )


def retained(batch):
    # Deliberately count each column reference, including repeated backing.
    return sum(
        buffer.size
        for column in batch.columns
        for buffer in column.buffers()
        if buffer is not None
    )


def stream(p, binding, batches, extent, **kwargs):
    value = p.interop_stream(binding, batches, extent, route="raw", **kwargs)
    value["rows"] = tagged(value["rows"])
    for snap in value["snapshots"]:
        snap["rows"] = tagged(snap["rows"])
    return value


def ipc_route(p, binding, batches, extent):
    frame, written = p.ipc_encode_observation(binding, batches, extent)
    assert frame is not None
    decoded = p.ipc_decode_observation(binding, frame, extent)
    decoded["rows"] = tagged(decoded["rows"])
    for snap in decoded["snapshots"]:
        snap["rows"] = tagged(snap["rows"])
    return dict(written=written, decoded=decoded, frame_bytes=len(frame)), frame


def routes(p, binding, rows, native, layout):
    from pietto._project import project_result_ingress as ingress

    pa = importlib.import_module("pyarrow")
    with ingress.ingest_rows(binding, rows) as managed:
        delivered = pa.record_batch(managed)
    result = dict(rows=observe(p, delivered))  # after exporter close
    batches = fragments(native, layout)
    result["stream"] = stream(p, binding, batches, len(rows))
    result["ipc"], _ = ipc_route(p, binding, batches, len(rows))
    return result


def native_alternative(p, batch):
    """Explicit SDK fixture at the input boundary; never a producer-row mapper."""
    pa = importlib.import_module("pyarrow")
    columns = list(batch.columns)
    for i, type_ in ((0, pa.int32()), (5, pa.large_string()), (7, pa.decimal256(9, 2))):
        columns[i] = pa.array(columns[i].to_pylist(), type=type_)
    columns[10] = columns[10].storage
    fields = expected(p, alternative=True)["fields"]
    schema = pa.schema(
        [
            pa.field(f["label"], col.type, nullable=f["nullable"])
            for f, col in zip(fields, columns, strict=True)
        ]
    )
    return pa.RecordBatch.from_arrays(columns, schema=schema)


def authority(p, root, built):
    from pietto._project import project_result_contract_correspondence as runtime
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project import project_result_binding as binding

    checked, _, artifact, contract, producer, _ = built
    foreign, _, foreign_artifact, other, _, _ = p.finite_fixture(
        root / "fresh", "postgres"
    )
    original = writer.export_result_contract(contract, checked)
    second = writer.export_result_contract(other, foreign)
    exact(original.canonical_bytes.decode(), second.canonical_bytes.decode())
    view = pure.decode_contract(original.canonical_bytes)
    with (
        patch.object(
            writer,
            "export_result_contract",
            side_effect=AssertionError("checker called writer"),
        ),
        patch.object(
            writer._Projection,
            "document",
            side_effect=AssertionError("checker called projection"),
        ),
    ):
        runtime.verify_contract_correspondence(view, other, foreign)
        runtime.verify_bound_export(original, checked)
        result = dict(
            pure_fresh=True,
            bound_fresh=p.refused(
                lambda: runtime.verify_bound_export(original, foreign)
            ),
            producer_fresh=p.refused(
                lambda: binding.verify_producer_binding(
                    producer, other, foreign_artifact
                )
            ),
            tail=p.refused(
                lambda: runtime.verify_contract_correspondence(
                    p.coherent_tail(view), contract, checked
                )
            ),
        )
    # Live replacement cannot inherit the original export merely by matching a schema.
    result["producer_contract"] = p.refused(
        lambda: binding.verify_producer_binding(
            replace(producer, contract=other), other, artifact
        )
    )
    return result


def ordered(p, root):
    root.mkdir(parents=True, exist_ok=True)
    from pietto._project import project_result_contract_portable as writer
    from pietto._project import project_result_contract_pure_boundary as pure
    from pietto._project import project_result_contract_correspondence as runtime

    result = {}
    for name in ("descriptors", "imported"):
        checked, contract = p.contract_fixture(root, name)
        exported = writer.export_result_contract(contract, checked)
        p.check_document_oracle(name, exported.canonical_bytes.decode())
        runtime.verify_bound_export(exported, checked)
        doc = exported.view.document
        key = doc["ordering"]["keys"][0]
        before = [key["direction"], key["expression"]["tag"]]
        key.update(authored_direction="asc", direction="asc")
        other = pure.decode_contract(pure.encode_document(doc))
        result[name] = dict(
            layer="descriptor-only",
            original=before,
            changed="asc",
            refusal=p.refused(
                lambda: runtime.verify_contract_correspondence(other, contract, checked)
            ),
        )
    return result


def adaptation(p, producer, foreign):
    from pietto._project import project_arrow_result as a

    fields = producer.fields
    choices = {
        "narrow": tuple(
            a.IntegerWidthRequest(b.field, 16) if i == 1 else None
            for i, b in enumerate(fields)
        ),
        "moved": (None, a.IntegerWidthRequest(fields[0].field, 32), *([None] * 11)),
        "foreign": (a.IntegerWidthRequest(foreign.fields[0].field, 32), *([None] * 12)),
        "repeated": (
            a.IntegerWidthRequest(fields[0].field, 32),
            a.IntegerWidthRequest(fields[0].field, 32),
            *([None] * 11),
        ),
    }
    with patch.object(
        a, "_arrow", side_effect=AssertionError("SDK before request validation")
    ):
        return {
            name: p.refused(
                lambda request=request: a.bind_arrow(producer, integer_widths=request)
            )
            for name, request in choices.items()
        }


def permutation(p, root):
    """A recompiled projection carries new field occurrences; old mapping is fixed."""
    from pietto._project.project_result_contract import build_result_contract
    from pietto._project.project_result_binding import bind_producer
    from pietto._project.project_sql_emission import emit_project_sql
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ingress as ingress

    pa = importlib.import_module("pyarrow")
    source = p.source("postgres").replace(
        "        renamed = id\n        other",
        "        other\n        renamed = id",
    )
    checked = p.build_neutral(root, {"main.pietto": source})
    emitted = emit_project_sql(checked, p.emission_input("postgres"))
    assert emitted.artifact is not None
    neutral = build_result_contract(checked)
    observations = tuple(
        replace(item, ordinal=i)
        for i, item in enumerate(reversed(p.observations("postgres")))
    )
    producer = bind_producer(neutral, emitted.artifact, observations)
    binding = a.bind_arrow(producer)
    with ingress.ingest_rows(binding, [[2, 1], [None, 3]]) as managed:
        out = p.finite_snapshot(pa.record_batch(managed))
    return dict(
        labels=[f["label"] for f in out["fields"]],
        rows=out["rows"],
        logical_fields=[f.label for f in neutral.shape.fields],
    )


def lifetime(p, binding, batch):
    from pietto._project import project_arrow_interop as interop
    import gc
    import weakref

    pa = importlib.import_module("pyarrow")
    source, owner = p.mutable_finite(batch)
    owner_ref = weakref.ref(owner)
    owned = interop.manage_batch(binding, source)
    lease = interop.BorrowLease(source, binding, owner, True)
    borrowed = interop.manage_batch(binding, source, lease=lease)
    try:
        owned_value, borrowed_value = pa.record_batch(owned), pa.record_batch(borrowed)
        owner.buffers[0, 1][:2] = (17).to_bytes(2, "little", signed=True)
    finally:
        owned.close()
        borrowed.close()
    del borrowed, owned, lease, source, owner
    gc.collect()
    result = dict(
        owned=observe(p, owned_value),
        borrowed=observe(p, borrowed_value),
        pinned=owner_ref() is not None,
    )
    del borrowed_value
    gc.collect()
    result["released"] = owner_ref() is None
    return result


def corruptions(p, binding, batch):
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_result_ingress as ingress

    pa = importlib.import_module("pyarrow")
    result = {}
    for name in MUTATIONS:
        if name == "column_swap":
            columns = list(batch.columns)
            columns[0], columns[12] = columns[12], columns[0]
            damaged = pa.RecordBatch.from_arrays(columns, schema=batch.schema)
        elif name == "reorder":
            damaged = batch.take(pa.array([1, 0, 2, 3], type=pa.int32()))
        elif name == "duplicate_loss":
            damaged = batch.slice(0, 3)
        elif name == "duplicate_replacement":
            damaged = batch.take(pa.array([0, 1, 2, 1], type=pa.int32()))
        else:
            index = {"value": 0, "signed_zero": 4, "null": 1}[name]
            values = batch.column(index).to_pylist()
            values[0] = {"value": 17, "signed_zero": 0.0, "null": None}[name]
            columns = list(batch.columns)
            columns[index] = pa.array(values, type=columns[index].type)
            damaged = pa.RecordBatch.from_arrays(columns, schema=batch.schema)
        with ingress.ingest_batch(binding, damaged) as managed:
            observed = observe(p, pa.record_batch(managed))
        route, _ = ipc_route(p, binding, [damaged], damaged.num_rows)
        result[name] = dict(
            rows=observed["rows"], valid=observed["valid"], ipc=route["decoded"]
        )
    original_copy = interop._copy_batch

    def defective(value, lease):
        copied = original_copy(value, lease)
        columns = list(copied.columns)
        values = columns[0].to_pylist()
        values[0] = 17
        columns[0] = pa.array(values, type=pa.int16())
        return pa.RecordBatch.from_arrays(columns, schema=copied.schema)

    with patch.object(interop, "_copy_batch", defective):
        with ingress.ingest_batch(binding, batch) as managed:
            result["injected"] = observe(p, pa.record_batch(managed))
    with ingress.ingest_batch(binding, batch) as restored:
        result["restored"] = observe(p, pa.record_batch(restored))
    return result


def ipc_integrity(p, binding, batch):
    import struct
    from pietto._project import project_result_ipc as ipc

    route, frame = ipc_route(p, binding, fragments(batch, (1, 3)), 4)
    damaged = bytearray(frame)
    damaged[99] ^= 1
    wrong_count = p.ipc_envelope(
        frame[100:], 4, 3, struct.unpack_from(">12sQQQ32s32s", frame)[4]
    )
    changed_rows = p.finite_rows("postgres")
    changed_rows[0][0] = 17
    from pietto._project import project_arrow_result as a

    altered = a.build_owned_batch(binding, changed_rows)
    altered_route, _ = ipc_route(p, binding, [altered], 4)
    return dict(
        header=100,
        ceiling=ipc.IPCLimits().max_bytes,
        original=route["decoded"],
        corrupted=p.ipc_decode_observation(binding, bytes(damaged), 4),
        wrong_batches=p.ipc_decode_observation(binding, wrong_count, 4),
        altered=altered_route["decoded"],
    )


def resources(p, binding, batch):
    from pietto._project import project_result_reader as r
    from pietto._project import project_arrow_result as a
    from pietto._project import project_arrow_interop as interop
    from pietto._project import project_result_ipc as ipc

    pa = importlib.import_module("pyarrow")
    result = {}
    for layout in ((4,), (1, 3)):
        batches = fragments(batch, layout)
        usages = [
            [part.num_rows, allowance(p.finite_snapshot(part)["rows"]), retained(part)]
            for part in batches
        ]
        cost = sum(max(logical, held) for _, logical, held in usages)
        exact_run = stream(
            p, binding, batches, 4, limits=r.FiniteReaderLimits(max_total_bytes=cost)
        )
        under = stream(
            p,
            binding,
            batches,
            4,
            limits=r.FiniteReaderLimits(max_total_bytes=cost - 1),
        )
        result[str(layout)] = dict(
            usages=usages, cost=cost, exact=exact_run, under=under
        )
    # Retained check and domain check are both invalid; copying must not run first.
    columns = list(batch.columns)
    columns[4] = pa.array([float("nan")] * 4, type=pa.float64())
    invalid = pa.RecordBatch.from_arrays(columns, schema=batch.schema).slice(0, 1)
    with patch.object(
        interop, "_copy_batch", side_effect=AssertionError("copy before validation")
    ):
        result["retained_before_domain"] = p.refused(
            lambda: interop.manage_batch(
                binding, invalid, limits=a.BatchLimits(bytes=retained(invalid) - 1)
            )
        )
    empty = batch.slice(0, 0)
    frame, _ = p.ipc_encode_observation(binding, [empty], 0)
    assert frame is not None
    exact_frame, admitted = p.ipc_encode_observation(
        binding, [empty], 0, cap=len(frame)
    )
    _, under = p.ipc_encode_observation(binding, [empty], 0, cap=len(frame) - 1)
    malformed = bytearray(frame)
    malformed[99] ^= 1
    with patch.object(
        a, "_arrow", side_effect=AssertionError("SDK before framing budget")
    ):
        preflight = p.refused(
            lambda: ipc.open_ipc(
                binding,
                bytes(malformed),
                expected_rows=0,
                ipc_limits=ipc.IPCLimits(len(frame) - 1),
            )
        )
    result["frame"] = dict(
        bytes=len(frame),
        admitted=admitted,
        under=under,
        equal=frame == exact_frame,
        preflight=preflight,
    )
    return result


def historical(cases):
    """References current full documents once; the orchestrator compares S14 bytes."""
    return {
        key: sorted(cases[key])
        for key in (
            "contract_documents",
            "scalar_codec",
            "text_codec",
            "decimal_codec",
            "temporal_codec",
            "finite_codec",
        )
    }


def run(p, root, cases):
    root.mkdir(parents=True, exist_ok=True)
    from pietto._project import project_arrow_result as a

    result: dict[str, Any] = {name: {} for name in GROUPS}
    for target in ("postgres", "mysql"):
        built = p.finite_fixture(root / target, target)
        nullable = p.finite_fixture(
            root / (target + "-nullable"), target, all_nullable=True
        )
        producer = built[4]
        binding = a.bind_arrow(producer, **p.finite_policy(producer))
        nbinding = a.bind_arrow(nullable[4], **p.finite_policy(nullable[4]))
        for state in STATES:
            selected = nbinding if state in ("null", "first_null") else binding
            rows = p.finite_rows(target, state=state)
            layout = (0, 1, 0, len(rows) - 1, 0) if rows else (0,)
            result[GROUPS[0]][target + "/" + state] = routes(
                p, selected, rows, p.native_finite(state=state), layout
            )
        policy = p.finite_policy(producer, wide=True)
        policy["integer_widths"] = (
            a.IntegerWidthRequest(producer.fields[0].field, 32),
            *([None] * 12),
        )
        policy["uuid_representations"] = tuple(
            a.UUIDRepresentationRequest(b.field, "binary16") if i in (10, 11) else None
            for i, b in enumerate(producer.fields)
        )
        alternative = a.bind_arrow(producer, **policy)
        result[GROUPS[2]][target] = dict(
            routes=routes(
                p,
                alternative,
                p.finite_rows(target),
                native_alternative(p, p.native_finite()),
                (1, 3),
            ),
            invalid=adaptation(p, producer, nullable[4]),
            null_invalid=adaptation(p, nullable[4], producer),
        )
        if target == "postgres":
            batch = p.native_finite()
            result[GROUPS[1]] = dict(
                layouts={
                    str(layout): stream(p, binding, fragments(batch, layout), 4)
                    for layout in LAYOUTS
                },
                bag_permutation=stream(
                    p,
                    binding,
                    [
                        batch.take(
                            importlib.import_module("pyarrow").array(
                                [1, 0, 2, 3],
                                type=importlib.import_module("pyarrow").int32(),
                            )
                        )
                    ],
                    4,
                ),
                order=ordered(p, root / "ordered"),
            )
            result[GROUPS[3]] = authority(p, root, built)
            result[GROUPS[4]] = dict(
                early=stream(p, binding, [batch], 4, early=True),
                trailing=stream(p, binding, [batch, batch.slice(0, 0)], 4),
                ipc_early=p.ipc_decode_observation(
                    binding, ipc_route(p, binding, [batch], 4)[1], 4, early=True
                ),
            )
            result[GROUPS[5]] = lifetime(p, binding, batch)
            result[GROUPS[6]] = ipc_integrity(p, binding, batch)
            result[GROUPS[7]] = resources(p, binding, batch)
            result[GROUPS[9]] = corruptions(p, binding, batch)
    result[GROUPS[2]]["projection"] = permutation(p, root / "permutation")
    result[GROUPS[8]] = historical(cases)
    verify({**cases, **result}, p)
    return result


def snapshot_check(actual, want):
    exact(actual, want)


def stream_check(value, want, layout):
    exact(value["rows"], want["rows"])
    exact(value["chunks"], list(layout))
    exact(value["before"], ["EXHAUSTED", "COMPLETE"])
    exact(value["after"], ["CLOSED", "COMPLETE"])
    exact(
        [
            value["source_complete"],
            value["error"],
            value["foreign_error"],
            value["closes"],
            value["reads"],
            value["pre_read"],
        ],
        [True, None, None, 1, len(layout) + 1, 0],
    )
    assert len(value["descriptors"]) == len(layout)
    offset = 0
    for snap, size in zip(value["snapshots"], layout, strict=True):
        snapshot_check(
            snap,
            dict(
                want,
                rows=want["rows"][offset : offset + size],
                valid=want["valid"][offset : offset + size],
            ),
        )
        offset += size


def decoded_check(value, want, layout):
    exact(value["rows"], want["rows"])
    exact(value["chunks"], list(layout))
    exact(
        [
            value["errors"],
            value["state"],
            value["ipc_complete"],
            value["source_complete"],
            value["receipt_identity"],
            value["reads"],
            value["closes"],
        ],
        [[], "CLOSED", True, True, True, len(layout) + 1, 1],
    )
    offset = 0
    for snap, size in zip(value["snapshots"], layout, strict=True):
        snapshot_check(
            snap,
            dict(
                want,
                rows=want["rows"][offset : offset + size],
                valid=want["valid"][offset : offset + size],
            ),
        )
        offset += size


def routes_check(value, want, layout):
    exact(sorted(value), ["ipc", "rows", "stream"])
    snapshot_check(value["rows"], want)
    stream_check(value["stream"], want, layout)
    decoded_check(value["ipc"]["decoded"], want, layout)
    written = value["ipc"]["written"]
    exact(
        [
            written["errors"],
            written["receipt"]["complete"],
            written["receipt"]["rows"],
            written["writes"],
        ],
        [[], True, len(want["rows"]), len(layout)],
    )
    exact(written["published_bytes"], value["ipc"]["frame_bytes"])


def verify(cases, p):
    try:
        _verify(cases, p)
    except (KeyError, TypeError, AttributeError, IndexError, AssertionError) as exc:
        raise ValueError("whole-result evidence shape or invariant") from exc


def _verify(cases, p):
    """Independent literal expectations plus already verified current group references."""
    # No Arrow import, compiler reconstruction, writer, or observed-value-as-oracle.
    values = cases[GROUPS[0]]
    exact(
        sorted(values),
        sorted(
            target + "/" + state for target in ("postgres", "mysql") for state in STATES
        ),
    )
    for name, value in values.items():
        state = name.split("/")[1]
        want = expected(p, state)
        count = len(want["rows"])
        layout = (0, 1, 0, count - 1, 0) if count else (0,)
        routes_check(value, want, layout)
    want = expected(p)
    rechunk = cases[GROUPS[1]]
    exact(sorted(rechunk["layouts"]), sorted(map(str, LAYOUTS)))
    for layout in LAYOUTS:
        stream_check(rechunk["layouts"][str(layout)], want, layout)
    permuted = dict(
        want,
        rows=tagged(changed(p.finite_expected()["rows"], "reorder")),
        valid=[want["valid"][i] for i in (1, 0, 2, 3)],
    )
    stream_check(rechunk["bag_permutation"], permuted, (4,))
    assert (
        bag(permuted["rows"]) == bag(want["rows"]) and permuted["rows"] != want["rows"]
    )
    exact(
        rechunk["order"],
        {
            name: dict(
                layer="descriptor-only",
                original=["desc", tag],
                changed="asc",
                refusal="CORRESPONDENCE",
            )
            for name, tag in (("descriptors", "name"), ("imported", "binary"))
        },
    )
    adaptations = cases[GROUPS[2]]
    for target in ("postgres", "mysql"):
        routes_check(
            adaptations[target]["routes"], expected(p, alternative=True), (1, 3)
        )
        for key in ("invalid", "null_invalid"):
            exact(
                adaptations[target][key],
                dict.fromkeys(
                    ("narrow", "moved", "foreign", "repeated"), "ARROW_ADAPTATION"
                ),
            )
    exact(
        adaptations["projection"],
        dict(
            labels=["other", "renamed"],
            rows=[[2, 1], [None, 3]],
            logical_fields=["other", "renamed"],
        ),
    )
    exact(
        cases[GROUPS[3]],
        dict(
            pure_fresh=True,
            bound_fresh="ROOT",
            producer_fresh="PRODUCER_ROOT",
            tail="CORRESPONDENCE",
            producer_contract="ROOT",
        ),
    )
    terminal = cases[GROUPS[4]]
    exact(
        [
            terminal["early"]["source_complete"],
            terminal["early"]["after"],
            terminal["early"]["source_rows"],
        ],
        [False, ["CLOSED_INCOMPLETE", "CLOSED_INCOMPLETE"], 4],
    )
    stream_check(terminal["trailing"], want, (4, 0))
    exact(
        [
            terminal["ipc_early"]["source_complete"],
            terminal["ipc_early"]["ipc_complete"],
            terminal["ipc_early"]["state"],
        ],
        [False, False, "CLOSED_INCOMPLETE"],
    )
    life = cases[GROUPS[5]]
    snapshot_check(life["owned"], want)
    snapshot_check(
        life["borrowed"],
        dict(want, rows=tagged(changed(p.finite_expected()["rows"], "value"))),
    )
    exact([life["pinned"], life["released"]], [True, True])
    integrity = cases[GROUPS[6]]
    exact([integrity["header"], integrity["ceiling"]], [100, 96 * 1024 * 1024])
    decoded_check(integrity["original"], want, (1, 3))
    altered = dict(want, rows=tagged(changed(p.finite_expected()["rows"], "value")))
    decoded_check(integrity["altered"], altered, (4,))
    exact(
        [integrity["corrupted"]["errors"], integrity["corrupted"]["ipc_complete"]],
        [["IPC_FRAME"], False],
    )
    exact(
        [
            integrity["wrong_batches"]["source_complete"],
            integrity["wrong_batches"]["ipc_complete"],
            integrity["wrong_batches"]["errors"],
        ],
        [True, False, ["IPC_COMPLETION"]],
    )
    resource = cases[GROUPS[7]]
    costs = []
    for layout in ((4,), (1, 3)):
        cell = resource[str(layout)]
        stream_check(cell["exact"], want, layout)
        # Four rows: fixed scalar storage + Bool bitmap + six NULL bitmaps,
        # two offset vectors and the authored 13 UTF-8 bytes. Slices retain all.
        backing = 4 * (2 + 4 + 8 + 8 + 16 + 32 + 8 + 16 + 16 + 2) + 1 + 6 + 12 * 5 + 13
        exact([item[0] for item in cell["usages"]], list(layout))
        offset = 0
        for size, logical, held in cell["usages"]:
            exact(
                logical, allowance(p.finite_expected()["rows"][offset : offset + size])
            )
            exact(held, backing)
            offset += size
        cost = sum(max(logical, held) for _, logical, held in cell["usages"])
        exact([cell["cost"], cell["exact"]["charge"]], [cost, cost])
        exact(
            cell["exact"]["descriptors"],
            [
                [size, logical, held, logical, held, 2 * held]
                for size, logical, held in cell["usages"]
            ],
        )
        exact(
            [cell["under"]["error"], cell["under"]["source_complete"]], ["LIMIT", False]
        )
        costs.append(cost)
    assert costs[1] > costs[0]
    exact(resource["retained_before_domain"], "LIMIT")
    frame = resource["frame"]
    exact(
        [
            frame["equal"],
            frame["preflight"],
            frame["admitted"]["published_bytes"],
            frame["under"]["errors"],
            frame["under"]["published_bytes"],
        ],
        [True, "LIMIT", frame["bytes"], ["LIMIT"], 0],
    )
    exact(cases[GROUPS[8]], historical(cases))
    assert sum(len(names) for names in historical(cases).values()) == 22
    mutations = cases[GROUPS[9]]
    for name in MUTATIONS:
        original = changed(p.finite_expected()["rows"], name)
        rows = tagged(original)
        exact(mutations[name]["rows"], rows)
        valid = [[v is not None for v in row] for row in original]
        exact(mutations[name]["valid"], valid)
        decoded_check(
            mutations[name]["ipc"], dict(want, rows=rows, valid=valid), (len(rows),)
        )
        assert rows != want["rows"]
        assert (bag(rows) == bag(want["rows"])) == (name == "reorder")
    snapshot_check(mutations["injected"], altered)
    snapshot_check(mutations["restored"], want)
    # These are current executions in this same required artifact, not old receipts.
    # Their complete existing checkers remain mandatory before this joint checker.
    assert cases["integration_terminal_failures"]["consumer"]["input_complete"] is True
    exact(cases["integration_terminal_failures"]["consumer"]["state"], "FAILED")
    exact(
        cases["c_stream_terminal"]["postgres"]["bridge_failure"]["primary"],
        "StopIteration",
    )
    exact(cases["ownership_transfer"]["postgres"]["copied_transfer"], "INTEROP_BINDING")
    exact(cases["contract_live_grafts"]["provenance"], ["FIELD", "FIELD"])


def damage():
    return (
        lambda v: v["cases"][GROUPS[0]]["postgres/values"]["rows"]["rows"][0][
            3
        ].__setitem__(0, "int"),
        lambda v: v["cases"][GROUPS[1]]["layouts"][str((0, 1, 0, 3, 0))][
            "chunks"
        ].pop(),
        lambda v: v["cases"][GROUPS[2]]["postgres"]["routes"]["rows"]["fields"][
            0
        ].update(label="merged"),
        lambda v: v["cases"][GROUPS[3]].update(bound_fresh="PASS"),
        lambda v: v["cases"][GROUPS[4]]["early"].update(source_complete=True),
        lambda v: v["cases"][GROUPS[5]].update(released=False),
        lambda v: v["cases"][GROUPS[6]]["wrong_batches"].update(ipc_complete=True),
        lambda v: v["cases"][GROUPS[7]][str((1, 3))].update(cost=0),
        lambda v: v["cases"][GROUPS[8]]["finite_codec"].pop(),
        lambda v: v["cases"][GROUPS[9]]["signed_zero"]["rows"][0][4].__setitem__(
            1, "8000000000000000"
        ),
    )
