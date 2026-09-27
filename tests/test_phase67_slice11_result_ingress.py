"""Inert ingress/delegation checks; real CPU carriers run in the installed probe."""

import importlib.util
from typing import Any, cast

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_interop as interop
from pietto._project import project_result_ingress as ingress
from pietto._project import project_result_reader as reader
from pietto._project.project_result_contract import ResultError


def test_row_and_batch_entries_reuse_actual_ownership_construction():
    assert ingress.ingest_rows is interop.build_managed_batch
    assert ingress.ingest_batch is interop.manage_batch
    assert ingress.__all__ == ()
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize("route", ("rows", "batch", "reader"))
def test_invalid_binding_is_rejected_before_any_optional_dependency(route):
    with pytest.raises(ResultError, match="ARROW_BINDING"):
        if route == "reader":
            ingress.ingest_reader(None, None, expected_rows=0)
        else:
            getattr(ingress, "ingest_" + route)(None, None)
    assert importlib.util.find_spec("pyarrow") is None


def test_required_reader_extent_is_a_native_signature_error():
    with pytest.raises(TypeError, match="expected_rows"):
        cast(Any, ingress.ingest_reader)(None, None)


@pytest.mark.parametrize("mode", ("lease", "acceptance", "composition"))
def test_acceptance_boundary_keeps_raw_lease_and_exact_cleanup_owner(monkeypatch, mode):
    binding, source, accepted, owner = object(), object(), object(), object()
    lease = interop.BorrowLease(source, cast(Any, binding), owner, True)
    events = []
    captured = (binding,)
    monkeypatch.setattr(interop, "_capture", lambda b: captured)

    def accept(b, s, **kwargs):
        events.append(("accept", b is binding, s is source, kwargs["expected_rows"]))
        if mode == "acceptance":
            raise ResultError("ARROW_SCHEMA")
        return accepted

    def compose(r, c, borrowed):
        events.append(
            (
                "compose",
                r is accepted,
                c is captured,
                borrowed[0] is lease,
                borrowed[1] is source,
            )
        )
        return accepted

    monkeypatch.setattr(reader, "open_finite_reader", accept)
    monkeypatch.setattr(interop, "_manage_accepted_reader", compose)
    if mode == "lease":
        object.__setattr__(lease, "source", object())
        with pytest.raises(ResultError, match="INTEROP_LEASE"):
            ingress.ingest_reader(binding, source, expected_rows=4, lease=lease)
        assert events == []
    elif mode == "acceptance":
        with pytest.raises(ResultError, match="ARROW_SCHEMA"):
            ingress.ingest_reader(binding, source, expected_rows=4, lease=lease)
        assert events == [("accept", True, True, 4)]
    else:
        assert (
            ingress.ingest_reader(binding, source, expected_rows=4, lease=lease)
            is accepted
        )
        assert events == [
            ("accept", True, True, 4),
            ("compose", True, True, True, True),
        ]


@pytest.mark.parametrize("cleanup", (False, True))
def test_accepted_composition_preserves_primary_and_closes_once(monkeypatch, cleanup):
    events = []
    primary = KeyboardInterrupt("injected claim failure")
    secondary = RuntimeError("injected cleanup failure")

    class Accepted:
        def close(self):
            events.append("close")
            if cleanup:
                raise secondary

    def fail(*args):
        raise primary

    monkeypatch.setattr(interop, "_check_binding", lambda captured: None)
    monkeypatch.setattr(interop.ManagedStream, "_initialize", fail)
    with pytest.raises(BaseExceptionGroup if cleanup else KeyboardInterrupt) as caught:
        interop._manage_accepted_reader(Accepted(), (), None)
    assert events == ["close"]
    if cleanup:
        assert isinstance(caught.value, BaseExceptionGroup)
        assert caught.value.exceptions == (primary, secondary)
    else:
        assert caught.value is primary


def test_current_exact_manifest_and_layout_arithmetic():
    assert len(probe.CASES) == len(set(probe.CASES)) == 102
    assert probe.CASES[84:92] == probe.INGRESS_GROUPS
    assert "project_result_ingress" in probe.PRODUCTS
    assert probe.INGRESS_USAGES == {
        "values": (630, 528),
        "empty": (12, 12),
        "null": (321, 274),
        "first_null": (778, 659),
    }
    expected = probe.ingress_stream_expected(
        probe.READER_LAYOUTS["uneven"], probe.finite_expected()["rows"]
    )
    assert expected["charge"] == 1584
    assert expected["chunks"] == [1, 2, 1]
    assert expected["pre_read"] == 0


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_real_source_binding_does_not_import_arrow(tmp_path, target):
    *_, producer, _ = probe.finite_fixture(tmp_path / target, target)
    assert len(producer.fields) == 13
    assert producer.contract.scalar_meaning is producer.artifact.request.scalar_meaning
    assert importlib.util.find_spec("pyarrow") is None
