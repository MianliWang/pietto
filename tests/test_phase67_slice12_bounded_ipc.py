"""Arrow-free framing/ownership checks; installed probe owns real SDK witnesses."""

import importlib.util
from types import SimpleNamespace
from typing import Any, cast

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_result_ingress as ingress
from pietto._project import project_result_ipc as ipc
from pietto._project.project_result_contract import ResultError


def test_private_inert_owner_and_exact_current_manifest():
    assert ipc.__all__ == ()
    assert importlib.util.find_spec("pyarrow") is None
    assert len(probe.CASES) == len(set(probe.CASES)) == 102
    assert probe.CASES[92:] == probe.IPC_GROUPS
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
        ipc=SimpleNamespace(open_stream=lambda data: opened),
        RecordBatchReader=SimpleNamespace(from_stream=handoff),
    )
    monkeypatch.setattr(ipc.arrow, "_arrow", lambda: sdk)
    if failure == "none":
        assert ipc._open_reader(b"payload") is accepted
        assert events == ["handoff"]
    else:
        with pytest.raises(
            BaseExceptionGroup if failure == "cleanup" else ResultError
        ) as caught:
            ipc._open_reader(b"payload")
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
        ipc, "_open_reader", lambda payload: pytest.fail("decoder invoked")
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
        monkeypatch.setattr(ipc, "_open_reader", lambda payload: object())
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
