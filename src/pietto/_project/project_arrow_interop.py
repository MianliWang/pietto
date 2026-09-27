"""Private CPU protocol exchange; buffer policy and C handle transfer are separate.

Cooperative providers and stable borrowed memory are caller obligations. Native
pointers are not sandboxed. Keep stream sessions alive through foreign use and
close them explicitly; foreign stream release alone is not finite completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from weakref import ref

from pietto._project import project_arrow_result as a
from pietto._project import project_result_reader as r
from pietto._project.project_result_contract import ResultError

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class BorrowLease:
    source: Any = field(repr=False)
    binding: a.ArrowResultBinding = field(repr=False)
    owner: Any = field(repr=False)
    non_mutation: bool


def _lease_capture(lease, source, binding):
    if lease is None:
        return None
    try:
        if (
            type(lease) is not BorrowLease
            or lease.source is not source
            or lease.binding is not binding
            or lease.owner is None
            or lease.non_mutation is not True
        ):
            raise ResultError("INTEROP_LEASE")
        return lease, source, binding, lease.owner
    except AttributeError as exc:
        raise ResultError("INTEROP_LEASE") from exc


def _check_lease(captured):
    if captured is not None:
        lease, source, binding, owner = captured
        actual = _lease_capture(lease, source, binding)
        if actual is None or actual[3] is not owner:
            raise ResultError("INTEROP_LEASE")


def _capture(binding):
    if type(binding) is not a.ArrowResultBinding:
        raise ResultError("ARROW_BINDING")
    a.verify_arrow_binding(binding, binding.producer)
    return binding, r._roots(binding), binding.schema, r._policy_snapshot(binding)


def _check_binding(captured):
    r._verify_binding_snapshot(*captured)


def _request(capsule, captured):
    _check_binding(captured)
    if capsule is None:
        return
    try:
        # Pinned SDK capsule import, never an integer-pointer interface.
        requested = a._arrow().Schema._import_from_c_capsule(capsule)
        a._verify_schema(requested, captured[0])
    except Exception as exc:
        raise ResultError("INTEROP_REQUEST") from exc


class _LeasedBuffer:
    def __init__(self, buffer, captured):
        self.buffer = buffer
        self.lease, _, _, self.owner = captured

    def __buffer__(self, flags):
        return memoryview(self.buffer)


def _copy_batch(batch, lease):
    """Flat finite storage only, after the original carrier has been checked."""
    pa = a._arrow()
    columns = []
    for column in batch.columns:
        extension = type(column.type) is type(pa.uuid())
        storage = column.storage if extension else column
        buffers = [
            None
            if buffer is None
            else pa.py_buffer(
                bytes(memoryview(buffer))
                if lease is None
                else _LeasedBuffer(buffer, lease)
            )
            for buffer in storage.buffers()
        ]
        copied = pa.Array.from_buffers(
            storage.type, len(storage), buffers, offset=storage.offset, null_count=-1
        )
        columns.append(
            pa.ExtensionArray.from_storage(column.type, copied) if extension else copied
        )
    return pa.RecordBatch.from_arrays(columns, schema=batch.schema)


def _export_array(batch):
    return batch.__arrow_c_array__()


class ManagedBatch:
    def __init__(self, binding, batch, *, lease=None, limits=a.BatchLimits()):
        captured = _capture(binding)
        borrowed = _lease_capture(lease, batch, binding)
        source_usage = a._checked_batch_usage(
            batch, binding, binding.producer, limits=limits
        )
        delivered = _copy_batch(batch, borrowed)
        usage = a._checked_batch_usage(
            delivered, binding, binding.producer, limits=limits
        )
        self._initialize(captured, delivered, borrowed, limits, source_usage, usage)

    def _initialize(self, captured, batch, lease, limits, source_usage, usage):
        self._captured = captured
        self._batch = batch
        self._batch_ref = ref(batch)
        self._lease = lease
        self._lease_original = lease
        self._limits = limits
        self._limit_values = (limits.fields, limits.rows, limits.bytes)
        self._closed = False
        self._policy = "owned_copy" if lease is None else "borrowed"
        self._initial_policy = self._policy
        self._needs_validation = lease is not None or any(
            buffer is not None and buffer.is_mutable
            for column in batch.columns
            for buffer in column.buffers()
        )
        self.source_usage = source_usage
        self.usage = usage

    @property
    def buffer_policy(self):
        return self._policy

    @property
    def schema(self):
        self._check()
        return self._captured[2]

    def _check(self):
        try:
            if self._closed:
                raise ResultError("INTEROP_CLOSED")
            if (
                self._batch is None
                or self._batch is not self._batch_ref()
                or self._policy != self._initial_policy
                or self._lease is not self._lease_original
                or (self._limits.fields, self._limits.rows, self._limits.bytes)
                != self._limit_values
            ):
                raise ResultError("INTEROP_BINDING")
            _check_binding(self._captured)
            _check_lease(self._lease)
        except (AttributeError, TypeError) as exc:
            raise ResultError("INTEROP_BINDING") from exc

    def __arrow_c_schema__(self):
        self._check()
        return self._captured[2].__arrow_c_schema__()

    def transfer(self):
        self._check()
        return BatchTransfer(self)

    def __arrow_c_array__(self, requested_schema=None):
        return self.transfer().__arrow_c_array__(requested_schema)

    def close(self):
        self._closed = True
        self._batch = None
        self._lease = self._lease_original = None

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *args):
        self.close()
        return False


class BatchTransfer:
    def __init__(self, managed):
        if type(managed) is not ManagedBatch:
            raise ResultError("INTEROP_BINDING")
        managed._check()
        self._identity = ref(self)
        self._managed = managed
        self._spent = False

    def __arrow_c_array__(self, requested_schema=None):
        if self._identity() is not self:
            raise ResultError("INTEROP_BINDING")
        if self._spent:
            raise ResultError("INTEROP_SPENT")
        managed = self._managed
        if managed is None:
            raise ResultError("INTEROP_SPENT")
        managed._check()
        _request(requested_schema, managed._captured)
        # Immutable copied bytes need no rescan; fresh SDK allocations can be mutable.
        if managed._needs_validation:
            a._checked_batch_usage(
                managed._batch,
                managed._captured[0],
                managed._captured[0].producer,
                limits=managed._limits,
            )
        self._spent = True
        try:
            return _export_array(managed._batch)
        finally:
            self._managed = None

    def close(self):
        self._spent = True
        self._managed = None


def manage_batch(binding, batch, *, lease=None, limits=a.BatchLimits()):
    return ManagedBatch(binding, batch, lease=lease, limits=limits)


def build_managed_batch(binding, rows, *, limits=a.BatchLimits()):
    captured = _capture(binding)
    batch, usage = a._build_owned_batch_with_usage(binding, rows, limits=limits)
    managed = object.__new__(ManagedBatch)
    managed._initialize(captured, batch, None, limits, usage, usage)
    return managed


def _cpu_hook(provider, name, device):
    hook = getattr(provider, name, None)
    if not callable(hook):
        raise ResultError(
            "INTEROP_DEVICE" if hasattr(provider, device) else "INTEROP_PROTOCOL"
        )
    return hook


class _ArrayProvider:
    def __init__(self, provider):
        self._hook = _cpu_hook(
            provider, "__arrow_c_array__", "__arrow_c_device_array__"
        )
        self._spent = False

    def __arrow_c_array__(self, requested_schema=None):
        if self._spent:
            raise ResultError("INTEROP_SPENT")
        self._spent = True
        value = self._hook(None)
        if type(value) is not tuple or len(value) != 2:
            raise ResultError("INTEROP_PROTOCOL")
        return value


def import_batch(binding, provider, *, lease=None, limits=a.BatchLimits()):
    captured = _capture(binding)
    borrowed = _lease_capture(lease, provider, binding)
    try:
        batch = a._arrow().record_batch(_ArrayProvider(provider))
    except ResultError:
        raise
    except Exception as exc:
        raise ResultError("INTEROP_PROTOCOL") from exc
    _check_binding(captured)
    _check_lease(borrowed)
    source_usage = a._checked_batch_usage(
        batch, binding, binding.producer, limits=limits
    )
    delivered = _copy_batch(batch, borrowed)
    usage = a._checked_batch_usage(delivered, binding, binding.producer, limits=limits)
    result = object.__new__(ManagedBatch)
    result._initialize(captured, delivered, borrowed, limits, source_usage, usage)
    return result


class _StreamProvider:
    def __init__(self, provider):
        self._hook = _cpu_hook(
            provider, "__arrow_c_stream__", "__arrow_c_device_stream__"
        )
        self._spent = False

    def __arrow_c_stream__(self, requested_schema=None):
        if self._spent:
            raise ResultError("INTEROP_SPENT")
        self._spent = True
        return self._hook(None)


def _close_bridge(bridge):
    bridge.close()


class _StreamBatches:
    def __init__(self, session):
        self._session = ref(session)

    def __iter__(self):
        return self

    def __next__(self):
        session = self._session()
        if session is None:
            raise ResultError("INTEROP_CLOSED")
        return session._next()


class ManagedStream:
    def __init__(self, reader, *, lease=None):
        if type(reader) is not r.CheckedFiniteReader:
            raise ResultError("READER_IDENTITY")
        reader._ensure_identity()
        captured = _capture(reader.expectation.binding)
        borrowed = _lease_capture(lease, reader, captured[0])
        self._initialize(reader, captured, borrowed)

    def _initialize(self, reader, captured, borrowed):
        self._identity = ref(self)
        self._reader = reader
        self._captured = captured
        self._lease = borrowed
        self._lease_original = borrowed
        self._token = reader._claim()
        self._state = "OPEN"
        self._bridge = None
        self._spent = False
        self._closed = False
        self._charge = 0
        self._descriptors: tuple[tuple[int, ...], ...] = ()
        self._primary_error: BaseException | None = None
        self._cleanup_errors: tuple[BaseException, ...] = ()

    @property
    def state(self):
        return self._state

    @property
    def input_completion(self):
        return self._reader.completion

    @property
    def charge(self):
        return self._charge

    @property
    def descriptors(self):
        return self._descriptors

    @property
    def primary_error(self):
        return self._primary_error

    @property
    def cleanup_errors(self):
        return self._cleanup_errors

    @property
    def schema(self):
        self._check()
        return self._captured[2]

    def _check(self):
        if self._identity() is not self:
            raise ResultError("INTEROP_BINDING")
        if self._closed:
            raise ResultError("INTEROP_CLOSED")
        if (
            self._reader._consumer is not self._token
            or self._lease is not self._lease_original
        ):
            raise ResultError("INTEROP_BINDING")
        self._reader._ensure_identity()
        _check_binding(self._captured)
        _check_lease(self._lease)

    def __arrow_c_schema__(self):
        self._check()
        return self._captured[2].__arrow_c_schema__()

    def __arrow_c_stream__(self, requested_schema=None):
        self._check()
        if self._spent:
            raise ResultError("INTEROP_SPENT")
        _request(requested_schema, self._captured)
        self._spent = True
        try:
            self._bridge = a._arrow().RecordBatchReader.from_batches(
                self._captured[2], _StreamBatches(self)
            )
            capsule = self._bridge.__arrow_c_stream__()
            self._state = "EXPORTED"
            return capsule
        except BaseException as exc:
            self._fail(exc)

    def _next(self):
        if self._closed:
            raise ResultError("INTEROP_CLOSED")
        if self._state == "FAILED":
            raise ResultError("INTEROP_TRANSFER")
        try:
            self._check()
        except BaseException as exc:
            self._fail(exc, during_pull=True)
        try:
            batch = self._reader._pull(self._token)
        except StopIteration:
            self._state = "EXHAUSTED"
            raise
        except BaseException as exc:
            self._fail(exc, during_pull=True)
        try:
            source_a, source_r = self._reader._observations[-1][3:]
            limits = self._reader.expectation.limits
            remaining = min(limits.batch.bytes, limits.max_total_bytes - self._charge)
            if max(source_a, source_r) > remaining:
                raise ResultError("LIMIT")
            delivered = _copy_batch(batch, self._lease)
            delivery_a, delivery_r = a._checked_batch_usage(
                delivered,
                self._captured[0],
                self._captured[0].producer,
                limits=a.BatchLimits(limits.batch.fields, limits.batch.rows, remaining),
            )
            charge = max(source_a, source_r, delivery_a, delivery_r)
            if self._charge + charge > limits.max_total_bytes:
                raise ResultError("LIMIT")
            self._descriptors += (
                (
                    batch.num_rows,
                    source_a,
                    source_r,
                    delivery_a,
                    delivery_r,
                    source_r + delivery_r if self._lease is None else 0,
                ),
            )
            self._charge += charge
            return delivered
        except BaseException as exc:
            self._fail(exc, during_pull=True)

    def _cleanup(self):
        if self._identity() is not self or self._closed:
            return
        self._closed = True
        errors = list(self._cleanup_errors)
        bridge, self._bridge = self._bridge, None
        if bridge is not None:
            try:
                _close_bridge(bridge)
            except BaseException as exc:
                errors.append(exc)
        try:
            self._reader.close()
        except BaseException as exc:
            errors.append(exc)
        self._lease = self._lease_original = None
        self._cleanup_errors = tuple(errors)
        if errors:
            self._state = "FAILED"
        elif self._state != "FAILED":
            self._state = (
                "CLOSED" if self._state == "EXHAUSTED" else "CLOSED_INCOMPLETE"
            )

    def _fail(self, error, *, during_pull=False):
        if self._identity() is not self:
            raise error
        self._state = "FAILED"
        self._primary_error = error
        if during_pull:
            # Never recursively close the bridge while its C get_next is active.
            try:
                self._reader.close()
            except BaseException as cleanup:
                self._cleanup_errors += (cleanup,)
        else:
            self._cleanup()
        if self._cleanup_errors:
            raise BaseExceptionGroup(
                "interop primary and cleanup failures", [error, *self._cleanup_errors]
            )
        if not isinstance(error, Exception) or isinstance(error, ResultError):
            raise error
        raise ResultError("INTEROP_TRANSFER") from error

    def close(self):
        if self._identity() is not self:
            raise ResultError("INTEROP_BINDING")
        if self._closed:
            return
        self._cleanup()
        if self._cleanup_errors:
            error = self._cleanup_errors[0]
            if len(self._cleanup_errors) > 1 or not isinstance(error, Exception):
                raise BaseExceptionGroup(
                    "interop cleanup failures", list(self._cleanup_errors)
                )
            raise ResultError("INTEROP_CLEANUP") from error

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, kind, error, traceback):
        if error is not None:
            self._fail(
                self._primary_error if self._primary_error is not None else error
            )
        self.close()
        return False

    def __del__(self):
        if hasattr(self, "_closed"):
            try:
                self._cleanup()
            except BaseException:
                pass  # Explicit close is the error-reporting path; GC is only fallback.


def manage_stream(reader, *, lease=None):
    return ManagedStream(reader, lease=lease)


def import_stream(
    binding, provider, *, expected_rows=None, limits=r.FiniteReaderLimits(), lease=None
):
    captured = _capture(binding)
    borrowed = _lease_capture(lease, provider, binding)
    # Reject invalid declarations before invoking a cooperative provider.
    values = r._limits_values(limits)
    if type(expected_rows) is not int or not 0 <= expected_rows <= values[1]:
        raise ResultError("READER_DECLARATION")
    try:
        source = a._arrow().RecordBatchReader.from_stream(_StreamProvider(provider))
    except ResultError:
        raise
    except Exception as exc:
        raise ResultError("INTEROP_PROTOCOL") from exc
    try:
        _check_binding(captured)
        _check_lease(borrowed)
        reader = r.open_finite_reader(
            binding, source, expected_rows=expected_rows, limits=limits
        )
    except BaseException as primary:
        try:
            source.close()
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "stream import and cleanup failures", [primary, cleanup]
            )
        raise
    return _manage_accepted_reader(reader, captured, borrowed)


def _manage_accepted_reader(reader, captured, borrowed):
    """Take cleanup responsibility only for an already accepted S09 session."""
    try:
        _check_binding(captured)
        _check_lease(borrowed)
        session = object.__new__(ManagedStream)
        session._initialize(reader, captured, borrowed)
        return session
    except BaseException as primary:
        try:
            reader.close()
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "stream composition and cleanup failures", [primary, cleanup]
            )
        raise
