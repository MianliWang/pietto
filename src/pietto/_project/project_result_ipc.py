"""Bounded private IPC bytes, never authentication or reconstructed authority."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import struct
from weakref import ref

from pietto._project import project_arrow_result as arrow
from pietto._project import project_result_ingress as ingress
from pietto._project import project_result_reader as reader
from pietto._project.project_result_contract import ResultError
from pietto._project.project_result_contract_portable import export_result_contract

__all__: tuple[str, ...] = ()

_HEADER = struct.Struct(">12sQQQ32s32s")
_MAGIC = b"PIETTO-IPC1\x00"
_MAX_BYTES = 96 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class IPCLimits:
    max_bytes: int = _MAX_BYTES


def _ceiling(limits):
    try:
        if (
            type(limits) is not IPCLimits
            or type(limits.max_bytes) is not int
            or not 0 <= limits.max_bytes <= _MAX_BYTES
        ):
            raise ResultError("LIMIT")
        return limits.max_bytes
    except AttributeError as exc:
        raise ResultError("LIMIT") from exc


def _extent(expected_rows, limits):
    values = reader._limits_values(limits)
    if type(expected_rows) is not int or not 0 <= expected_rows <= values[1]:
        raise ResultError("READER_DECLARATION")
    return values


def _contract_digest(binding):
    ingress.interop._capture(binding)
    return contract_digest(binding.producer.contract)


def contract_digest(contract):
    """Exact output-contract identity carried by every frame header."""
    from pietto._project.project_sql_plan_verification import (
        CompiledSQLPlanVerification,
    )

    if type(contract.authority) is not CompiledSQLPlanVerification:
        return hashlib.sha256(
            export_result_contract(contract, contract.authority).canonical_bytes
        ).digest()
    # Source-free compiled roots have no portable source document; their
    # identity is the pinned root plus the complete checked public shape.
    from pietto._project.project_compiled_schema import _wire
    from pietto._project.project_result_contract import verify_result_contract
    from pietto._project.project_scalar_meaning import TimestampMeaning

    verify_result_contract(contract, contract.authority)
    root = contract.authority.completed.root
    fields = []
    for leaf in contract.shape.fields:
        law = None if leaf.meaning is None else leaf.meaning.law
        fields.append(
            [
                leaf.ordinal,
                leaf.label,
                leaf.shape.canonical.kind.value,
                leaf.shape.canonical.name,
                leaf.nullability.value,
                None
                if law is None
                else [
                    "timestamp",
                    law.calendar,
                    law.resolution,
                    law.timezone,
                    list(law.lower),
                    list(law.upper),
                ]
                if type(law) is TimestampMeaning
                else ["uuid", law.byte_order, law.byte_width],
            ]
        )
    document = {
        "fields": fields,
        "format": "pietto.compiled-result-contract.v1",
        "multiplicity": contract.multiplicity.value,
        "pin": root.expected_pin,
        "query": _wire(root.description.query),
    }
    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
    ).digest()


class _BoundedSink(io.BytesIO):
    def __init__(self, ceiling):
        super().__init__()
        self.ceiling = ceiling

    def write(self, data):
        if self.tell() + len(data) > self.ceiling:
            raise ResultError("LIMIT")
        return super().write(data)


def encode_ipc(
    binding,
    source,
    *,
    expected_rows,
    reader_limits=reader.FiniteReaderLimits(),
    ipc_limits=IPCLimits(),
) -> bytes:
    contract = _contract_digest(binding)
    ceiling = _ceiling(ipc_limits)
    if ceiling < _HEADER.size:
        raise ResultError("LIMIT")
    session = ingress.ingest_reader(
        binding, source, expected_rows=expected_rows, limits=reader_limits
    )
    sink = writer = consumer = None
    errors: list[BaseException] = []
    payload = None
    batches = 0
    try:
        sink = _BoundedSink(ceiling - _HEADER.size)
        pa = arrow._arrow()
        consumer = pa.RecordBatchReader.from_stream(session)
        writer = pa.ipc.new_stream(
            sink,
            binding.schema,
            options=pa.ipc.IpcWriteOptions(
                metadata_version=pa.ipc.MetadataVersion.V5,
                use_legacy_format=False,
                allow_64bit=False,
                compression=None,
            ),
        )
        for batch in consumer:
            # SDK C-imported empty slices can retain an offset with zero-sized
            # buffers, which the IPC writer mis-sizes. Admission and accounting
            # already checked the original carrier; keep this empty batch.
            if batch.num_rows == 0 and any(column.offset for column in batch.columns):
                batch = batch.take(pa.array([], type=pa.int32()))
            writer.write_batch(batch, custom_metadata=None)
            batches += 1
        completion = session.input_completion
        reader.verify_finite_completion(
            session._reader, session._reader.expectation, completion
        )
        if completion.batches != batches:
            raise ResultError("IPC_COMPLETION")
        finished, writer = writer, None
        finished.close()
        consumer.close()
        consumer = None
        session.close()
        if session.state != "CLOSED" or _contract_digest(binding) != contract:
            raise ResultError("IPC_COMPLETION")
        payload = sink.getvalue()
    except BaseException as primary:
        errors.append(
            session.primary_error if session.primary_error is not None else primary
        )
    finally:
        for resource in (writer, consumer, session, sink):
            if resource is not None:
                try:
                    resource.close()
                except BaseException as cleanup:
                    errors.append(cleanup)
    if len(errors) > 1:
        raise BaseExceptionGroup("IPC write and cleanup failures", errors)
    if errors:
        error = errors[0]
        if isinstance(error, ResultError) or not isinstance(error, Exception):
            raise error
        raise ResultError("IPC_WRITE") from error
    assert type(payload) is bytes
    return (
        _HEADER.pack(
            _MAGIC,
            expected_rows,
            batches,
            len(payload),
            contract,
            hashlib.sha256(payload).digest(),
        )
        + payload
    )


def _frame(data, expected_rows, reader_limits, ipc_limits):
    if type(data) is not bytes:
        raise ResultError("IPC_FRAME")
    ceiling = _ceiling(ipc_limits)
    if len(data) < _HEADER.size:
        raise ResultError("IPC_FRAME")
    claims = _HEADER.unpack_from(data)
    magic, rows, batches, size, _, digest = claims
    if magic != _MAGIC or len(data) != _HEADER.size + size:
        raise ResultError("IPC_FRAME")
    if len(data) > ceiling:
        raise ResultError("LIMIT")
    values = _extent(expected_rows, reader_limits)
    if rows != expected_rows:
        raise ResultError("IPC_EXTENT")
    if batches > values[0]:
        raise ResultError("LIMIT")
    payload = memoryview(data)[_HEADER.size :]
    if hashlib.sha256(payload).digest() != digest:
        raise ResultError("IPC_FRAME")
    return claims, payload


def open_ipc(
    binding,
    frame,
    *,
    expected_rows,
    reader_limits=reader.FiniteReaderLimits(),
    ipc_limits=IPCLimits(),
):
    claims, payload = _frame(frame, expected_rows, reader_limits, ipc_limits)
    if _contract_digest(binding) != claims[4]:
        raise ResultError("IPC_CONTRACT")
    source = _open_reader(payload)
    managed = ingress._ingest_reader(
        binding, source, expected_rows, reader_limits, None, owned=True
    )
    try:
        return IPCStream(binding, frame, claims, managed)
    except BaseException as primary:
        try:
            managed.close()
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "IPC session construction and cleanup failures", [primary, cleanup]
            )
        raise


class IPCStream:
    """Retain immutable frame claims; all consumption state belongs to S09/S10."""

    def __init__(self, binding, frame, claims, managed):
        self._identity = ref(self)
        self._binding, self._frame, self._claims, self._managed = (
            binding,
            frame,
            claims,
            managed,
        )
        self._original = (binding, frame, claims, managed)

    def _identity_check(self):
        try:
            if self._identity() is not self or any(
                a is not b
                for a, b in zip(
                    (self._binding, self._frame, self._claims, self._managed),
                    self._original,
                    strict=True,
                )
            ):
                raise ResultError("IPC_IDENTITY")
        except (AttributeError, TypeError, ValueError) as exc:
            if isinstance(exc, ResultError):
                raise
            raise ResultError("IPC_IDENTITY") from exc

    def _check(self):
        self._identity_check()
        self._managed._reader._check_original()
        if (
            _HEADER.unpack_from(self._frame) != self._claims
            or _contract_digest(self._binding) != self._claims[4]
        ):
            raise ResultError("IPC_IDENTITY")

    @property
    def state(self):
        return self._managed.state

    @property
    def primary_error(self):
        return self._managed.primary_error

    @property
    def input_completion(self):
        return self._managed.input_completion

    @property
    def completion(self):
        if self._managed.state != "CLOSED":
            return None
        return verify_ipc_completion(self)

    def __arrow_c_stream__(self, requested_schema=None):
        self._check()
        return self._managed.__arrow_c_stream__(requested_schema)

    def close(self):
        self._identity_check()
        self._managed.close()

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *args):
        self._identity_check()
        return self._managed.__exit__(*args)


def verify_ipc_completion(session):
    if type(session) is not IPCStream:
        raise ResultError("IPC_IDENTITY")
    session._check()
    managed = session._managed
    completion = managed.input_completion
    if (
        managed.state != "CLOSED"
        or managed.primary_error is not None
        or managed.cleanup_errors
    ):
        raise ResultError("IPC_COMPLETION")
    reader.verify_finite_completion(
        managed._reader, managed._reader.expectation, completion
    )
    if (
        completion.binding is not session._binding
        or completion.rows != session._claims[1]
        or completion.batches != session._claims[2]
    ):
        raise ResultError("IPC_COMPLETION")
    return completion


def _open_reader(payload):
    pa = arrow._arrow()
    try:
        opened = pa.ipc.open_stream(payload)
    except Exception as exc:
        raise ResultError("IPC_READ") from exc
    try:
        # IPC returns a subclass; the SDK handoff owns its native reader and
        # yields the exact RecordBatchReader accepted by the existing ingress.
        return pa.RecordBatchReader.from_stream(opened)
    except BaseException as primary:
        try:
            opened.close()
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "IPC reader handoff and cleanup failures", [primary, cleanup]
            )
        if not isinstance(primary, Exception):
            raise
        raise ResultError("IPC_READ") from primary
