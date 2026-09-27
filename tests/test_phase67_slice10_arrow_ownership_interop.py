"""Arrow-free lease/grant checks; actual C consumers live in the installed probe."""

from dataclasses import replace
import gc
import importlib.util
from typing import Any, cast
import weakref

import pytest

import _pietto_phase67_result_product_probe as probe
from pietto._project import project_arrow_interop as interop
from pietto._project import project_result_reader as reader
from pietto._project.project_result_contract import ResultError


@pytest.mark.parametrize(
    "change", ("source", "binding", "owner", "commitment", "deleted")
)
def test_lease_requires_exact_source_binding_owner_and_explicit_commitment(change):
    source, binding, owner = object(), object(), object()
    lease = interop.BorrowLease(source, cast(Any, binding), owner, True)
    if change == "source":
        lease = replace(lease, source=object())
    elif change == "binding":
        lease = replace(lease, binding=cast(Any, object()))
    elif change == "owner":
        lease = replace(lease, owner=None)
    elif change == "commitment":
        lease = replace(lease, non_mutation=False)
    else:
        object.__delattr__(lease, "non_mutation")
    with pytest.raises(ResultError, match="INTEROP_LEASE"):
        interop._lease_capture(lease, source, binding)
    assert importlib.util.find_spec("pyarrow") is None


def test_python_buffer_exporter_pins_original_owner_without_copying():
    source, binding = object(), object()
    owner = probe.InteropOwner()
    reference = weakref.ref(owner)
    backing = bytearray(b"abc")
    lease = interop.BorrowLease(source, cast(Any, binding), owner, True)
    captured = interop._lease_capture(lease, source, binding)
    pin = interop._LeasedBuffer(backing, captured)
    view = memoryview(pin)
    del owner, lease, captured, pin
    gc.collect()
    assert reference() is not None
    backing[0] = ord("z")
    assert bytes(view) == b"zbc"
    view.release()
    del view
    gc.collect()
    assert reference() is None


def test_lease_owner_substitution_is_rejected_against_original_capture():
    source, binding = object(), object()
    lease = interop.BorrowLease(source, cast(Any, binding), object(), True)
    captured = interop._lease_capture(lease, source, binding)
    object.__setattr__(lease, "owner", object())
    with pytest.raises(ResultError, match="INTEROP_LEASE"):
        interop._check_lease(captured)


def test_claimed_reader_rejects_direct_competing_pull_before_source_access():
    session = object.__new__(reader.CheckedFiniteReader)
    session._consumer = object()
    with pytest.raises(ResultError, match="READER_CLAIMED"):
        session.read_next_batch()


@pytest.mark.parametrize("kind", ("array", "stream"))
def test_device_only_hook_is_not_invoked(kind):
    class Device:
        def __getattr__(self, name):
            if name == "__arrow_c_device_" + kind + "__":
                return lambda: pytest.fail("device hook invoked")
            raise AttributeError(name)

    with pytest.raises(ResultError, match="INTEROP_DEVICE"):
        interop._cpu_hook(
            Device(), "__arrow_c_" + kind + "__", "__arrow_c_device_" + kind + "__"
        )


def test_private_origin_and_exact_group_inventory():
    assert interop.__all__ == ()
    assert "project_arrow_interop" in probe.PRODUCTS
    assert len(probe.CASES) == len(set(probe.CASES)) == 84
    assert tuple(probe.CASES[-10:]) == probe.INTEROP_GROUPS
    assert importlib.util.find_spec("pyarrow") is None


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_real_finite_binding_remains_arrow_free_until_protocol_use(tmp_path, target):
    from pietto._project import project_arrow_result as a

    *_, producer, _ = probe.finite_fixture(tmp_path / target, target)
    with pytest.raises(ResultError, match="ARROW_DEPENDENCY_MISSING"):
        a.bind_arrow(producer, **probe.finite_policy(producer))


def test_context_preserves_original_control_instead_of_foreign_wrapper(monkeypatch):
    session = object.__new__(interop.ManagedStream)
    original = KeyboardInterrupt()
    session._primary_error = original

    def fail(error):
        raise error

    monkeypatch.setattr(session, "_fail", fail)
    with pytest.raises(KeyboardInterrupt) as raised:
        session.__exit__(ValueError, ValueError("foreign wrapper"), None)
    assert raised.value is original


@pytest.mark.parametrize("kind", ("transfer", "stream"))
def test_copied_handles_cannot_reuse_original_grant_or_cleanup(kind):
    from copy import copy

    cls = interop.BatchTransfer if kind == "transfer" else interop.ManagedStream
    original = cast(Any, object.__new__(cls))
    original._identity = weakref.ref(original)
    original._closed = True
    original._spent = False
    cloned = copy(original)
    action = (
        cloned.__arrow_c_array__ if kind == "transfer" else cloned.__arrow_c_stream__
    )
    with pytest.raises(ResultError, match="INTEROP_BINDING"):
        action()
    if kind == "stream":
        with pytest.raises(ResultError, match="INTEROP_BINDING"):
            cloned.close()
