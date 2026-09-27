"""Checked finite consumption relative to an explicit caller-declared extent.

The caller supplies a fresh exclusive CPU reader and stable batches. Neither
this declaration nor normal EOF authenticates an original query or its values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn
from weakref import ref

from pietto._project import project_arrow_result as arrow
from pietto._project.project_result_contract import ResultError

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FiniteReaderLimits:
    batch: arrow.BatchLimits = arrow.BatchLimits()
    max_batches: int = 1024
    max_total_rows: int = 1048576
    max_total_bytes: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True, eq=False)
class FiniteResultExpectation:
    binding: arrow.ArrowResultBinding = field(repr=False)
    expected_rows: int
    limits: FiniteReaderLimits
    _source_ref: Any = field(repr=False)
    _session: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class BatchDescriptor:
    ordinal: int
    row_start: int
    rows: int
    logical_bytes: int
    retained_bytes: int


@dataclass(frozen=True, slots=True, eq=False)
class FiniteCompletion:
    expectation: FiniteResultExpectation = field(repr=False)
    binding: arrow.ArrowResultBinding = field(repr=False)
    descriptors: tuple[BatchDescriptor, ...]
    rows: int
    batches: int
    charge: int
    pulls: int
    _source_ref: Any = field(repr=False)
    _session: Any = field(repr=False)
    _terminal: Any = field(repr=False)


def _limits_values(limits):
    try:
        if (
            type(limits) is not FiniteReaderLimits
            or type(limits.batch) is not arrow.BatchLimits
        ):
            raise ResultError("LIMIT")
        values = (
            limits.max_batches,
            limits.max_total_rows,
            limits.max_total_bytes,
            limits.batch.fields,
            limits.batch.rows,
            limits.batch.bytes,
        )
        if any(
            type(v) is not int or not 0 <= v <= cap
            for v, cap in zip(
                values,
                (1024, 1048576, 64 * 1024 * 1024, 64, 4096, 8 * 1024 * 1024),
                strict=True,
            )
        ):
            raise ResultError("LIMIT")
        return values
    except (AttributeError, TypeError) as exc:
        raise ResultError("LIMIT") from exc


def _roots(binding):
    producer = binding.producer
    contract = producer.contract
    return (
        producer,
        producer.fields,
        contract,
        producer.artifact,
        contract.authority,
        contract.shape,
        contract.scalar_meaning,
        *(
            value
            for bound in producer.fields
            for value in (bound.observation, bound.observation.protocol_nullable)
        ),
    )


def _policy_snapshot(binding):
    return tuple(
        (
            name,
            getattr(binding, name),
            tuple(
                None
                if request is None
                else (request, request.field, getattr(request, value))
                for request in (getattr(binding, name) or ())
            ),
            value,
        )
        for name, value in (
            ("integer_widths", "bits"),
            ("text_offset_widths", "bits"),
            ("decimal_widths", "bits"),
            ("uuid_representations", "representation"),
            ("field_labels", "label"),
        )
    )


def _verify_binding_snapshot(binding, roots, schema, policies):
    try:
        if binding.schema is not schema or any(
            a is not b for a, b in zip(_roots(binding), roots, strict=True)
        ):
            raise ResultError("READER_IDENTITY")
        for name, requests, captured, attribute in policies:
            if getattr(binding, name) is not requests:
                raise ResultError("READER_IDENTITY")
            for item in captured:
                if item is not None:
                    request, field_, value = item
                    actual = getattr(request, attribute)
                    if (
                        request.field is not field_
                        or type(actual) is not type(value)
                        or actual != value
                    ):
                        raise ResultError("READER_IDENTITY")
        arrow.verify_arrow_binding(binding, binding.producer)
    except (AttributeError, TypeError, IndexError) as exc:
        raise ResultError("READER_IDENTITY") from exc


def _read_source(source):
    return source.read_next_batch()


def _close_source(source):
    source.close()


def _make_completion(reader):
    expected = reader._expectation
    return FiniteCompletion(
        expected,
        expected.binding,
        tuple(BatchDescriptor(*row) for row in reader._observations),
        reader._rows,
        len(reader._observations),
        reader._charge,
        reader._pulls,
        expected._source_ref,
        expected._session,
        reader._terminal,
    )


class CheckedFiniteReader:
    """One pull session; use completion only relative to its original expectation."""

    def __init__(
        self, binding, source, *, expected_rows=None, limits=FiniteReaderLimits()
    ):
        values = _limits_values(limits)
        if type(expected_rows) is not int or not 0 <= expected_rows <= values[1]:
            raise ResultError("READER_DECLARATION")
        if type(binding) is not arrow.ArrowResultBinding:
            raise ResultError("ARROW_BINDING")
        arrow.verify_arrow_binding(binding, binding.producer)
        pa = arrow._arrow()
        if type(source) is not pa.RecordBatchReader:
            raise ResultError("READER_SOURCE")
        arrow._dimensions(len(source.schema), 0, limits.batch)
        arrow._verify_schema(source.schema, binding)
        expected = FiniteResultExpectation(
            binding, expected_rows, limits, ref(source), object()
        )
        self._expectation = expected
        self._captured = (
            expected,
            binding,
            expected._source_ref,
            expected._session,
            expected_rows,
            limits,
            values,
            _roots(binding),
            binding.schema,
            _policy_snapshot(binding),
            ref(self),
        )
        # Acceptance: all checks above leave an unsuccessful source with its caller.
        self._source = source
        self._consumer = None
        self._state = "OPEN"
        self._observations: tuple[tuple[int, ...], ...] = ()
        self._rows = self._charge = self._pulls = 0
        self._normal_end = self._close_attempted = self._close_succeeded = False
        self._primary_error: BaseException | None = None
        self._cleanup_error: BaseException | None = None
        self._terminal: object | None = None
        self._completion: FiniteCompletion | None = None

    @property
    def expectation(self):
        return self._expectation

    @property
    def state(self):
        return self._state

    @property
    def schema(self):
        self._ensure_identity()
        return self._captured[8]

    @property
    def rows(self):
        return self._rows

    @property
    def batch_count(self):
        return len(self._observations)

    @property
    def charge(self):
        return self._charge

    @property
    def pulls(self):
        return self._pulls

    @property
    def primary_error(self):
        return self._primary_error

    @property
    def cleanup_error(self):
        return self._cleanup_error

    @property
    def completion(self):
        if self._state == "OPEN":
            self._ensure_identity()
            return None
        if self._state != "COMPLETE":
            return None
        try:
            verify_finite_completion(self, self._expectation, self._completion)
        except BaseException as exc:
            self._fail(exc, "READER_VALIDATION")
        return self._completion

    def _check_original(self):
        try:
            (
                expected,
                binding,
                source,
                session,
                rows,
                limits,
                values,
                roots,
                schema,
                policies,
                owner,
            ) = self._captured
            if (
                owner() is not self
                or self._expectation is not expected
                or expected.binding is not binding
                or expected._source_ref is not source
                or expected._session is not session
                or type(expected.expected_rows) is not int
                or expected.expected_rows != rows
                or expected.limits is not limits
                or _limits_values(limits) != values
                or (
                    self._state == "OPEN"
                    and (self._source is None or self._source is not source())
                )
            ):
                raise ResultError("READER_IDENTITY")
            _verify_binding_snapshot(binding, roots, schema, policies)
        except (AttributeError, TypeError, IndexError) as exc:
            raise ResultError("READER_IDENTITY") from exc

    def _ensure_identity(self):
        try:
            self._check_original()
        except BaseException as exc:
            self._fail(exc, "READER_VALIDATION")

    def _close_once(self):
        if self._close_attempted:
            return self._cleanup_error
        self._close_attempted = True
        try:
            original = self._captured[2]()
            if original is None:
                raise ResultError("READER_CLEANUP")
            _close_source(original)
            self._close_succeeded = True
        except BaseException as exc:
            self._cleanup_error = exc
        finally:
            self._source = None
        return self._cleanup_error

    def _fail(self, error: BaseException, category: str) -> NoReturn:
        self._state = "FAILED"
        self._primary_error = error
        cleanup = self._close_once()
        if cleanup is error and not isinstance(error, Exception):
            raise error
        if cleanup is not None:
            error.add_note(f"source cleanup also failed: {type(cleanup).__name__}")
            if not isinstance(cleanup, Exception):
                raise BaseExceptionGroup(
                    "finite reader primary and cleanup failures", [error, cleanup]
                )
        if not isinstance(error, Exception):
            raise error
        if isinstance(error, ResultError) and category == "READER_VALIDATION":
            raise error
        cause = (
            error
            if cleanup is None
            else ExceptionGroup("finite reader failures", [error, cleanup])
        )
        raise ResultError(category) from cause

    def _finish(self):
        try:
            self._check_original()
            if self._rows != self._captured[4]:
                raise ResultError("READER_EXTENT")
            self._normal_end = True
            cleanup = self._close_once()
            if cleanup is not None:
                if not isinstance(cleanup, Exception):
                    raise cleanup
                raise ResultError("READER_CLEANUP") from cleanup
            self._terminal = object()
            self._completion = _make_completion(self)
            self._state = "COMPLETE"
            verify_finite_completion(self, self._expectation, self._completion)
        except BaseException as exc:
            self._fail(exc, "READER_VALIDATION")
        raise StopIteration

    def _claim(self):
        self._ensure_identity()
        if self._state != "OPEN" or self._pulls != 0 or self._consumer is not None:
            raise ResultError("READER_CLAIMED")
        self._consumer = object()
        return self._consumer

    def read_next_batch(self):
        return self._pull(None)

    def _pull(self, consumer):
        if self._consumer is not None and consumer is not self._consumer:
            raise ResultError("READER_CLAIMED")
        if self._state == "COMPLETE":
            self.completion
            raise StopIteration
        if self._state != "OPEN":
            raise ResultError(
                "READER_FAILED" if self._state == "FAILED" else "READER_CLOSED"
            )
        self._ensure_identity()
        self._pulls += 1
        try:
            batch = _read_source(self._source)
        except StopIteration:
            return self._finish()
        except BaseException as exc:
            self._fail(exc, "READER_SOURCE")
        try:
            self._check_original()
            pa = arrow._arrow()
            if not isinstance(batch, pa.RecordBatch) or not batch.is_cpu:
                raise ResultError("ARROW_BATCH")
            limits = self._expectation.limits
            if len(self._observations) >= limits.max_batches:
                raise ResultError("LIMIT")
            arrow._dimensions(batch.num_columns, batch.num_rows, limits.batch)
            arrow._verify_schema(batch.schema, self._expectation.binding)
            if self._rows + batch.num_rows > self._captured[4]:
                raise ResultError("READER_EXTENT")
            remaining = min(limits.batch.bytes, limits.max_total_bytes - self._charge)
            allowance, retained = arrow._checked_batch_usage(
                batch,
                self._expectation.binding,
                self._expectation.binding.producer,
                limits=arrow.BatchLimits(
                    limits.batch.fields, limits.batch.rows, remaining
                ),
            )
            descriptor = (
                len(self._observations),
                self._rows,
                batch.num_rows,
                allowance,
                retained,
            )
            self._observations += (descriptor,)
            self._rows += batch.num_rows
            self._charge += max(allowance, retained)
            return batch
        except BaseException as exc:
            self._fail(exc, "READER_VALIDATION")

    def close(self):
        if self._state != "OPEN":
            return
        self._ensure_identity()
        self._state = "CLOSED_INCOMPLETE"
        cleanup = self._close_once()
        if cleanup is not None:
            self._state = "FAILED"
            if not isinstance(cleanup, Exception):
                raise cleanup
            raise ResultError("READER_CLEANUP") from cleanup

    def __iter__(self):
        return self

    def __next__(self):
        return self.read_next_batch()

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        if error is not None and self._state == "OPEN":
            self._state = "FAILED"
            self._primary_error = error
            cleanup = self._close_once()
            if cleanup is not None:
                error.add_note(f"source cleanup also failed: {type(cleanup).__name__}")
                if not isinstance(cleanup, Exception):
                    raise BaseExceptionGroup(
                        "finite reader context and cleanup failures", [error, cleanup]
                    )
        else:
            self.close()
        return False


def open_finite_reader(
    binding, source, *, expected_rows=None, limits=FiniteReaderLimits()
):
    return CheckedFiniteReader(
        binding, source, expected_rows=expected_rows, limits=limits
    )


def verify_finite_completion(reader, expectation, completion) -> None:
    """Check captured session observations independently; never pull or rebuild."""
    try:
        if type(reader) is not CheckedFiniteReader:
            raise ResultError("READER_IDENTITY")
        reader._check_original()
        if (
            type(expectation) is not FiniteResultExpectation
            or expectation is not reader._captured[0]
            or type(completion) is not FiniteCompletion
            or completion is not reader._completion
            or reader._state != "COMPLETE"
            or reader._normal_end is not True
            or reader._close_attempted is not True
            or reader._close_succeeded is not True
            or reader._source is not None
            or reader._primary_error is not None
            or reader._cleanup_error is not None
            or completion.expectation is not expectation
            or completion.binding is not reader._captured[1]
            or completion._source_ref is not reader._captured[2]
            or completion._session is not reader._captured[3]
            or completion._terminal is not reader._terminal
            or reader._terminal is None
            or type(completion.descriptors) is not tuple
            or len(completion.descriptors) != len(reader._observations)
        ):
            raise ResultError("READER_IDENTITY")
        rows = charge = 0
        for ordinal, (entry, original) in enumerate(
            zip(completion.descriptors, reader._observations, strict=True)
        ):
            if type(entry) is not BatchDescriptor:
                raise ResultError("READER_IDENTITY")
            actual = (
                entry.ordinal,
                entry.row_start,
                entry.rows,
                entry.logical_bytes,
                entry.retained_bytes,
            )
            if (
                any(type(n) is not int or n < 0 for n in actual)
                or actual != original
                or entry.ordinal != ordinal
                or entry.row_start != rows
                or entry.rows > expectation.limits.batch.rows
                or max(entry.logical_bytes, entry.retained_bytes)
                > expectation.limits.batch.bytes
            ):
                raise ResultError("READER_IDENTITY")
            rows += entry.rows
            charge += max(entry.logical_bytes, entry.retained_bytes)
        batches = len(completion.descriptors)
        if (
            any(
                type(n) is not int
                for n in (
                    completion.rows,
                    completion.batches,
                    completion.charge,
                    completion.pulls,
                    reader._rows,
                    reader._charge,
                    reader._pulls,
                )
            )
            or rows != completion.rows
            or rows != reader._rows
            or rows != reader._captured[4]
            or batches != completion.batches
            or batches > expectation.limits.max_batches
            or charge != completion.charge
            or charge != reader._charge
            or charge > expectation.limits.max_total_bytes
            or completion.pulls != reader._pulls
            or completion.pulls != batches + 1
        ):
            raise ResultError("READER_IDENTITY")
    except (AttributeError, TypeError, IndexError) as exc:
        raise ResultError("READER_IDENTITY") from exc
