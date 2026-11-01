"""Arrow-free framing/ownership checks; installed probe owns real SDK witnesses."""

import importlib.util
import struct
from types import SimpleNamespace
from typing import Any, cast

import pytest

import _pietto_results_product as probe
from pietto._project import project_result_ingress as ingress
from pietto._project import project_result_ipc as ipc
from pietto._project.project_result_contract import ResultError


def test_private_inert_owner_and_exact_current_manifest():
    assert ipc.__all__ == ()
    assert importlib.util.find_spec("pyarrow") is None
    assert len(probe.CASES) == len(set(probe.CASES))
    assert probe.CASES[92:102] == probe.IPC_GROUPS
    assert "project_result_ipc" in probe.PRODUCTS


@pytest.mark.parametrize("value", (True, False, -1, 1.0, None, 100663297))
def test_encoded_limit_only_accepts_exact_tightening(value):
    with pytest.raises(ResultError, match="LIMIT"):
        ipc._ceiling(ipc.IPCLimits(cast(Any, value)))


@pytest.mark.parametrize("value", (0, 100, 100663296))
def test_zero_and_hard_encoded_limit_are_valid(value):
    assert ipc._ceiling(ipc.IPCLimits(value)) == value


@pytest.mark.parametrize("value", (True, -1, None, 1.0, 1048577))
def test_decode_extent_is_explicit_before_optional_sdk(value):
    with pytest.raises(ResultError, match="READER_DECLARATION"):
        ipc.open_ipc(None, probe.ipc_envelope(b"payload", 4), expected_rows=value)


def test_required_extent_is_not_reconstructed_from_envelope():
    data = probe.ipc_envelope(b"payload", 4)
    with pytest.raises(TypeError, match="expected_rows"):
        cast(Any, ipc.open_ipc)(None, data)
    with pytest.raises(ResultError, match="IPC_EXTENT"):
        ipc.open_ipc(None, data, expected_rows=3)
    with pytest.raises(ResultError, match="ARROW_BINDING"):
        ipc.open_ipc(None, data, expected_rows=4)
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize("offset", (0, 11, 19, 35, 68, 99, 100, 106))
def test_framing_damage_rejects_before_sdk(offset):
    data = bytearray(probe.ipc_envelope(b"payload", 4))
    data[offset] ^= 1
    with pytest.raises(ResultError, match="IPC_(FRAME|EXTENT)"):
        ipc.open_ipc(None, bytes(data), expected_rows=4)


def test_exact_bytes_bounded_view_and_independent_report_digest():
    data = probe.ipc_envelope(b"payload", 4)
    claims, view = ipc._frame(
        data, 4, ipc.reader.FiniteReaderLimits(), ipc.IPCLimits(len(data))
    )
    assert claims[1:4] == (4, 1, 7)
    assert bytes(view) == b"payload" and view.obj is data
    for invalid in (bytearray(data), memoryview(data), data[:-1], data + b"x"):
        with pytest.raises(ResultError, match="IPC_FRAME"):
            ipc.open_ipc(None, invalid, expected_rows=4)
    with pytest.raises(ResultError, match="LIMIT"):
        ipc.open_ipc(None, data, expected_rows=4, ipc_limits=ipc.IPCLimits(106))
    observed = probe.ipc_frame_observation(data)
    assert probe.verify_ipc_frame(observed, 4) == data
    observed["payload_sha256"] = "00" * 32
    with pytest.raises(ValueError, match="digest"):
        probe.verify_ipc_frame(observed, 4)


@pytest.mark.parametrize("failure", ("none", "handoff", "cleanup"))
def test_ipc_sdk_reader_handoff_owns_cleanup_without_relaxing_ingress(
    monkeypatch, failure
):
    events = []
    primary = ValueError("injected handoff failure")
    secondary = RuntimeError("injected original close failure")
    accepted = object()

    class Opened:
        def close(self):
            events.append("close")
            if failure == "cleanup":
                raise secondary

    opened = Opened()

    def handoff(source):
        assert source is opened
        events.append("handoff")
        if failure != "none":
            raise primary
        return accepted

    sdk = SimpleNamespace(
        py_buffer=bytes,
        ipc=SimpleNamespace(
            MessageReader=_message_reader(()), open_stream=lambda data: opened
        ),
        RecordBatchReader=SimpleNamespace(from_stream=handoff),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: sdk)
    if failure == "none":
        assert ipc._open_reader(b"payload", 1024) is accepted
        assert events == ["handoff"]
    else:
        with pytest.raises(
            BaseExceptionGroup if failure == "cleanup" else ResultError
        ) as caught:
            ipc._open_reader(b"payload", 1024)
        assert events == ["handoff", "close"]
        if failure == "cleanup":
            assert isinstance(caught.value, BaseExceptionGroup)
            assert caught.value.exceptions == (primary, secondary)
        else:
            assert caught.value.__cause__ is primary


@pytest.mark.parametrize("owned", (False, True))
@pytest.mark.parametrize("cleanup", (False, True))
def test_ingress_preaccept_close_depends_on_actual_source_ownership(
    monkeypatch, owned, cleanup
):
    events = []
    primary = ResultError("ARROW_SCHEMA")
    secondary = RuntimeError("injected source close failure")

    def fail(binding):
        raise primary

    def close(source):
        events.append(source)
        if cleanup:
            raise secondary

    source = object()
    monkeypatch.setattr(ingress.interop, "_capture", fail)
    monkeypatch.setattr(ingress.reader, "_close_source", close)
    with pytest.raises(
        BaseExceptionGroup if owned and cleanup else ResultError
    ) as caught:
        ingress._ingest_reader(
            None, source, 0, ipc.reader.FiniteReaderLimits(), None, owned=owned
        )
    assert events == ([source] if owned else [])
    if owned and cleanup:
        assert isinstance(caught.value, BaseExceptionGroup)
        assert caught.value.exceptions == (primary, secondary)
    else:
        assert caught.value is primary


@pytest.mark.parametrize("cap", (0, 2, 5))
def test_bounded_sink_rejects_before_growing(cap):
    sink = ipc._BoundedSink(cap)
    assert sink.write(b"a" * cap) == cap
    with pytest.raises(ResultError, match="LIMIT"):
        sink.write(b"x")
    assert sink.getvalue() == b"a" * cap
    sink.close()


def test_header_batch_cap_and_contract_digest_precede_sdk(monkeypatch):
    data = probe.ipc_envelope(b"payload", 4, batches=1025)
    with pytest.raises(ResultError, match="LIMIT"):
        ipc.open_ipc(None, data, expected_rows=4)
    monkeypatch.setattr(ipc, "_contract_digest", lambda binding: b"x" * 32)
    monkeypatch.setattr(
        ipc, "_open_reader", lambda payload, budget: pytest.fail("decoder invoked")
    )
    with pytest.raises(ResultError, match="IPC_CONTRACT"):
        ipc.open_ipc(None, probe.ipc_envelope(b"payload", 4), expected_rows=4)


def test_fixed_header_has_no_trailer_and_exposes_all_independent_claims():
    import hashlib
    import struct

    canonical = hashlib.sha256(b"canonical").digest()
    frame = probe.ipc_envelope(b"payload", 4, 2, canonical)
    assert len(frame) == 107 and ipc._HEADER.size == 100
    assert struct.unpack_from(">12sQQQ32s32s", frame) == (
        b"PIETTO-IPC1\0",
        4,
        2,
        7,
        canonical,
        hashlib.sha256(b"payload").digest(),
    )
    assert frame[100:] == b"payload"
    assert (
        probe.verify_ipc_frame(probe.ipc_frame_observation(frame), 4, 2, canonical)
        == frame
    )


def test_no_unconstructed_or_foreign_completion_authority():
    with pytest.raises(ResultError, match="IPC_IDENTITY"):
        ipc.verify_ipc_completion(None)


@pytest.mark.parametrize("stage", ("sink", "wrapper"))
@pytest.mark.parametrize("cleanup", (False, True))
def test_accepted_construction_failure_closes_once_and_preserves_control(
    monkeypatch, stage, cleanup
):
    primary = KeyboardInterrupt("injected construction failure")
    secondary = RuntimeError("injected accepted cleanup failure")
    closes = []

    def close():
        closes.append("close")
        if cleanup:
            raise secondary

    managed = SimpleNamespace(primary_error=None, close=close)
    monkeypatch.setattr(ipc, "_contract_digest", lambda binding: bytes(32))

    def fail(*args, **kwargs):
        raise primary

    if stage == "sink":
        monkeypatch.setattr(ingress, "ingest_reader", lambda *a, **k: managed)
        monkeypatch.setattr(ipc, "_BoundedSink", fail)
    else:
        monkeypatch.setattr(ipc, "_open_reader", lambda payload, budget: object())
        monkeypatch.setattr(ingress, "_ingest_reader", lambda *a, **k: managed)
        monkeypatch.setattr(ipc, "IPCStream", fail)
    with pytest.raises(BaseExceptionGroup if cleanup else KeyboardInterrupt) as caught:
        if stage == "sink":
            ipc.encode_ipc(None, None, expected_rows=0)
        else:
            ipc.open_ipc(None, probe.ipc_envelope(b"payload", 4), expected_rows=4)
    assert closes == ["close"]
    if cleanup:
        assert isinstance(caught.value, BaseExceptionGroup)
        assert caught.value.exceptions == (primary, secondary)
    else:
        assert caught.value is primary


def test_partial_ipc_wrapper_cannot_claim_completion():
    session = object.__new__(ipc.IPCStream)
    with pytest.raises(ResultError, match="IPC_IDENTITY"):
        ipc.verify_ipc_completion(session)


def _message_reader(items, events=None):
    """Arrow-free ``pa.ipc.MessageReader``: yields items, raising exceptions."""
    stream = iter(items)

    def read_next_message():
        if events is not None:
            events.append("message")
        item = next(stream)  # StopIteration ends the stream, as in pyarrow
        if isinstance(item, BaseException):
            raise item
        return item

    reader = SimpleNamespace(read_next_message=read_next_message)
    return SimpleNamespace(open_stream=lambda buffer: reader)


def _flatbuffer(*slots, header=4):
    """Message (header in slot 2) -> RecordBatch whose vtable lists ``slots``."""
    vtable = struct.pack(f"<HH{len(slots)}H", 4 + 2 * len(slots), 8, *slots)
    vtable += bytes(-len(vtable) % 4)
    batch = 24 + len(vtable)
    return (
        struct.pack("<I", 16)  # root: the Message table at 16
        + struct.pack("<5H2x", 10, 8, 0, 0, header)  # 4: Message vtable
        + struct.pack("<iI", 12, batch - 20)  # 16: Message table; 20: header
        + vtable  # 24: RecordBatch vtable
        + struct.pack("<iI", batch - 24, 0)  # the RecordBatch table
    )


KEY = b"ARROW:experimental_compression"


def _message(version, *keys):
    """Message (version, header, custom_metadata) -> RecordBatch without the
    compression slot; each custom_metadata key is valued ``zstd``."""
    data = bytearray()

    def put(form, *values):
        data.extend(struct.pack(form, *values))
        return len(data) - struct.calcsize(form)

    def point(at, target):  # a uoffset field
        struct.pack_into("<I", data, at, target - at)

    def text(value):
        at = put(f"<I{len(value)}sx", len(value), value)
        data.extend(bytes(-len(data) % 4))
        return at

    put("<I28x", 32)  # root: the Message table at 32
    # vtables: Message at 4 (version entry at 8, custom_metadata entry at 16),
    # RecordBatch at 20, KeyValue at 24 (key entry at 28)
    struct.pack_into("<7H2x2H4H", data, 4, 14, 16, 4, 0, 8, 0, 12, 4, 4, 8, 12, 4, 8)
    put("<ih2x2I", 28, version, 0, 0)  # 36: version; 40: header; 44: entries
    point(40, put("<i", 28))  # 48: a RecordBatch without fields
    point(44, put("<I", len(keys)))  # 52: the custom_metadata vector
    slots = [put("<I", 0) for _ in keys]
    for slot, key in zip(slots, keys):
        pair = put("<i2I", len(data) - 24, 0, 0)  # KeyValue (the first at 60)
        point(slot, pair)
        point(pair + 4, text(key))  # the first key at 72
        point(pair + 8, text(b"zstd"))
    return bytes(data)


def _patched(at, form, value, base=None):
    data = bytearray(base or _flatbuffer(0, 0, 0, 4))
    struct.pack_into(form, data, at, value)
    return bytes(data)


SCHEMA = SimpleNamespace(type="schema", metadata=b"")
PLAIN = SimpleNamespace(type="record batch", metadata=_flatbuffer(0, 0, 0, 0))
COMPRESSED = SimpleNamespace(type="record batch", metadata=_flatbuffer(0, 0, 0, 4))
DICTIONARY = SimpleNamespace(type="dictionary", metadata=b"")


@pytest.mark.parametrize(
    "messages,admitted,reads,budget",
    (
        ((SCHEMA, PLAIN, PLAIN), True, 4, 1024),
        ((), True, 1, 1024),
        ((SCHEMA, DICTIONARY, PLAIN), False, 2, 1024),
        ((SCHEMA, PLAIN, COMPRESSED), False, 3, 1024),
        # Framing damage ends the walk; the reader stops at the same message,
        # so the later compressed body is never decoded.
        ((SCHEMA, OSError("cut body"), COMPRESSED), True, 2, 1024),
        ((SCHEMA, PLAIN, ValueError("cut metadata")), True, 3, 1024),
        # The walk ends where the reader must: the schema, the budget's batches
        # and the one more the reader decodes before LIMIT; it sees no further.
        ((SCHEMA, PLAIN, PLAIN, COMPRESSED), True, 3, 1),
        ((SCHEMA, PLAIN, COMPRESSED), False, 3, 1),
        ((SCHEMA, PLAIN, COMPRESSED), True, 2, 0),
        ((SCHEMA, COMPRESSED), False, 2, 0),
    ),
)
def test_payload_admission_inspects_messages_before_the_decoder(
    monkeypatch, messages, admitted, reads, budget
):
    events = []
    accepted = object()
    sdk = SimpleNamespace(
        py_buffer=lambda data: events.append("buffer") or data,
        ipc=SimpleNamespace(
            MessageReader=_message_reader(messages, events),
            open_stream=lambda data: events.append("open_stream") or data,
        ),
        RecordBatchReader=SimpleNamespace(from_stream=lambda source: accepted),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: sdk)
    if admitted:
        assert ipc._open_reader(b"payload", budget) is accepted
    else:
        with pytest.raises(ResultError, match="^IPC_ENCODING$") as caught:
            ipc._open_reader(b"payload", budget)
        assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert events == ["buffer"] + ["message"] * reads + ["open_stream"] * admitted


def test_payload_admission_preserves_control_flow(monkeypatch):
    interrupt = KeyboardInterrupt("injected")
    sdk = SimpleNamespace(
        py_buffer=bytes,
        ipc=SimpleNamespace(
            MessageReader=_message_reader((SCHEMA, interrupt)),
            open_stream=lambda data: pytest.fail("decoder invoked"),
        ),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: sdk)
    with pytest.raises(KeyboardInterrupt) as caught:
        ipc._open_reader(b"payload", 1024)
    assert caught.value is interrupt


def test_open_orders_frame_contract_admission_then_decoder(monkeypatch):
    events = []
    sdk = SimpleNamespace(
        py_buffer=bytes,
        ipc=SimpleNamespace(
            MessageReader=_message_reader((SCHEMA, COMPRESSED), events),
            open_stream=lambda data: pytest.fail("decoder invoked"),
        ),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: events.append("sdk") or sdk)
    monkeypatch.setattr(
        ipc, "_contract_digest", lambda binding: events.append("contract") or bytes(32)
    )
    data = probe.ipc_envelope(b"payload", 4)
    with pytest.raises(ResultError, match="IPC_FRAME"):
        ipc.open_ipc(None, data[:-1], expected_rows=4)
    assert events == []
    foreign = probe.ipc_envelope(b"payload", 4, contract_digest=b"x" * 32)
    with pytest.raises(ResultError, match="IPC_CONTRACT"):
        ipc.open_ipc(None, foreign, expected_rows=4)
    assert events == ["contract"]
    with pytest.raises(ResultError, match="IPC_ENCODING"):
        ipc.open_ipc(None, data, expected_rows=4)
    assert events == ["contract", "contract", "sdk", "message", "message"]


@pytest.mark.parametrize(
    "limits",
    (ipc.reader.FiniteReaderLimits(), ipc.reader.FiniteReaderLimits(max_batches=3)),
)
def test_open_bounds_admission_by_the_reader_batch_budget(monkeypatch, limits):
    budgets = []

    def admit(pa, payload, max_batches):
        budgets.append(max_batches)
        raise ResultError("IPC_ENCODING")

    monkeypatch.setattr(ipc, "_contract_digest", lambda binding: bytes(32))
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: None)
    monkeypatch.setattr(ipc, "_admit_payload", admit)
    data = probe.ipc_envelope(b"payload", 4)
    with pytest.raises(ResultError, match="IPC_ENCODING"):
        ipc.open_ipc(None, data, expected_rows=4, reader_limits=limits)
    assert budgets == [limits.max_batches]


@pytest.mark.parametrize(
    "metadata,compressed",
    (
        (_flatbuffer(0, 0, 0, 4), True),
        (_flatbuffer(0, 0, 0, 0), False),  # the slot is present but zero
        (_flatbuffer(0, 0, 0), False),  # the vtable ends before the slot
        (_flatbuffer(0, 0, 0, 4, header=0), False),  # no header table
    ),
)
def test_compression_is_the_presence_of_the_record_batch_slot(metadata, compressed):
    assert ipc._compressed(metadata) is compressed


@pytest.mark.parametrize(
    "metadata,compressed",
    (
        (_message(3, KEY), True),  # V4 names a codec under Arrow 0.17's key
        (_message(3, b"other", KEY), True),  # any entry
        (_message(3, KEY[:-1], KEY + b"!", b"other"), False),  # the exact key only
        (_message(3), False),  # empty custom_metadata
        (_message(4, KEY), False),  # V5 never reads the key
        (_patched(8, "<H", 0, _message(3, KEY)), False),  # no version: V1
        (_patched(16, "<H", 0, _message(3, KEY)), False),  # no custom_metadata
        (_patched(28, "<H", 0, _message(3, KEY)), False),  # a KeyValue without key
    ),
)
def test_v4_custom_metadata_codec_key_is_compression(metadata, compressed):
    assert ipc._compressed(metadata) is compressed


def test_v4_custom_metadata_scans_every_bounded_entry():
    assert ipc._compressed(_message(3, *([b"other"] * 1023), KEY))
    with pytest.raises(ResultError, match="^IPC_READ$"):
        ipc._compressed(_message(3, *([b"other"] * 1025)))


def test_malformed_message_reader_open_falls_back_to_ipc_read(monkeypatch):
    raw = ValueError("malformed stream")
    sdk = SimpleNamespace(
        py_buffer=bytes,
        ipc=SimpleNamespace(
            MessageReader=SimpleNamespace(
                open_stream=lambda payload: (_ for _ in ()).throw(raw)
            ),
            open_stream=lambda payload: (_ for _ in ()).throw(raw),
        ),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: sdk)
    with pytest.raises(ResultError, match="^IPC_READ$") as caught:
        ipc._open_reader(b"payload", 1024)
    assert caught.value.__cause__ is raw


@pytest.mark.parametrize(
    "metadata",
    (
        b"",
        b"\0\0\0",
        _patched(0, "<I", 42),  # Message table past the end
        _patched(16, "<i", 20),  # Message vtable before the start
        _patched(16, "<i", -40),  # Message vtable past the end
        _patched(20, "<I", 1000),  # header table past the end
        _patched(36, "<i", 100),  # RecordBatch vtable before the start
        _patched(44, "<I", 1000, _message(3, KEY)),  # custom_metadata past the end
        _patched(52, "<I", 1000, _message(3, b"other")),  # entries past the end
        _patched(72, "<I", 1000, _message(3, KEY)),  # key bytes past the end
    ),
)
def test_derived_positions_are_bounds_checked_never_wrapped(metadata):
    with pytest.raises(ResultError, match="^IPC_READ$"):
        ipc._compressed(metadata)
