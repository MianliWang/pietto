"""Small live-record framing and failure-order laws before native acceptance."""

import json
from types import SimpleNamespace
from threading import RLock

from _pietto_phase68_slice9_probe import native_data
from pietto._project.project_execution_postgres_adbc_native import (
    NativeReply,
    NativeStatement,
)


def test_native_reply_serializer_is_explicit_and_lossless():
    reply = NativeReply(
        "SELECT $1,'雪'".encode(), (1,), ((True, None, "text"),), "NORMAL"
    )
    document = json.loads(json.dumps(native_data(reply)))
    assert document == {
        "sql": "SELECT $1,'雪'",
        "arguments": [1],
        "rows": [[True, None, "text"]],
        "terminal": "NORMAL",
    }


def test_reader_close_does_not_mask_primary_or_run_twice():
    calls = []

    def fail():
        calls.append("reader.close")
        raise RuntimeError("injected cleanup failure")

    owner = SimpleNamespace(
        _statements=[], _cleanup_errors=[], _gate=RLock(), _active=None
    )
    statement = NativeStatement(owner, b"SELECT 1", (), (), "query", copy=True)
    statement.reader = SimpleNamespace(close=fail)
    primary = ValueError("injected read error")
    statement._close_reader(primary)
    statement.close()
    assert calls == ["reader.close"]
    assert len(owner._cleanup_errors) == 1
    assert owner._cleanup_errors[0].phase == "reader_close"
    assert statement.reader is None and statement.reader_close == "FAILED"


def test_unimported_stream_is_released_before_statement():
    calls = []

    class Handle:
        is_valid = True

        def release(self):
            calls.append("stream.release")
            self.is_valid = False

    owner = SimpleNamespace(
        _statements=[], _cleanup_errors=[], _gate=RLock(), _active=None
    )
    statement = NativeStatement(owner, b"SELECT 1", (), (), "query", copy=True)
    statement.stream_handle = Handle()
    statement.native = SimpleNamespace(close=lambda: calls.append("statement.close"))
    statement.close()
    statement.close()
    assert calls == ["stream.release", "statement.close"]


def test_reset_releases_only_owned_role_database_acl_before_drop(monkeypatch):
    import _pietto_phase68_slice9_probe as probe

    calls = []

    def manager(resource, sql):
        calls.append(sql)
        return (
            [("pietto_query",), ("pietto_subset",)]
            if sql.startswith("SELECT rolname")
            else ()
        )

    monkeypatch.setattr(probe, "manager", manager)
    probe.reset_fixture_database(object())
    for role in ("pietto_query", "pietto_subset"):
        revoke = f'REVOKE ALL PRIVILEGES ON DATABASE phase66 FROM "{role}"'
        assert calls.index(revoke) < calls.index(f'DROP ROLE "{role}"')
    assert "SET search_path=public" in calls


def test_observer_does_not_materialize_unrelated_compiler_locals():
    from _pietto_phase68_slice9_probe import Calls

    class Frame:
        f_code = SimpleNamespace(co_filename="/unrelated_compiler.py", co_name="verify")

        @property
        def f_locals(self):
            raise AssertionError("unrelated locals were materialized")

    observer = object.__new__(Calls)
    observer.previous = None
    observer.native_path = "/native.py"
    observer.owner_path = "/owner.py"
    observer.enumeration_path = "/enumeration.py"
    observer.observe(Frame(), "call", None)


def test_full_campaign_readiness_rejects_stale_producing_inputs(tmp_path):
    import hashlib
    import pytest
    from _pietto_phase68_slice9_probe import check_readiness

    wheel = tmp_path / "test-only.whl"
    wheel.write_bytes(b"independent input bytes")
    path = tmp_path / "readiness.json"
    inputs = {"files": {"src/a.py": "original"}}
    ready = {
        "status": "GREEN_FOR_CURRENT_INPUTS",
        "tree": "candidate",
        "inputs": inputs["files"],
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }
    path.write_text(json.dumps(ready))
    assert check_readiness(path, "candidate", inputs, wheel) == ready
    with pytest.raises(ValueError, match="READINESS_REQUIRED"):
        check_readiness(None, "candidate", inputs, wheel)
    for tree, supplied in (
        ("different", inputs),
        ("candidate", {"files": {"src/a.py": "changed"}}),
    ):
        with pytest.raises(ValueError, match="READINESS_CHANGED"):
            check_readiness(path, tree, supplied, wheel)
    wheel.write_bytes(b"replaced wheel")
    with pytest.raises(ValueError, match="READINESS_CHANGED"):
        check_readiness(path, "candidate", inputs, wheel)
